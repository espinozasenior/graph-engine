"""
A custom import hook for instrumenting Python code.

This module provides functionality to automatically instrument
Python code loaded from a specified directory, tracking function calls
and other relevant metrics for dependency analysis.
"""

import ast
import importlib.abc
import importlib.util
import os
import sys
import types
from pathlib import Path
import logging
import queue
import threading
import time
import hashlib
import pickle
import re
from typing import Dict, List, Optional, Set, Tuple, Any, Union, Pattern


# Global queue for function call events
function_call_queue = queue.Queue()
# Set of files being monitored
monitored_files: Set[str] = set()
# Lock for thread-safe operations
_lock = threading.Lock()

# Configure logger
logger = logging.getLogger(__name__)


class FunctionCallEvent:
    """Class to represent a function call event."""
    
    def __init__(self, function_name: str, module_name: str, filename: str):
        """Initialize a function call event.
        
        Args:
            function_name: Name of the called function
            module_name: Name of the module containing the function
            filename: Path to the file containing the function
        """
        self.function_name = function_name
        self.module_name = module_name
        self.filename = filename
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        """Return a string representation of the event."""
        return f"{self.module_name}.{self.function_name} called at {self.timestamp} in {self.filename}"


class InstrumentationTransformer(ast.NodeTransformer):
    """AST transformer that adds instrumentation to function definitions."""
    
    def __init__(self, module_name: str, filename: str):
        """Initialize the transformer.
        
        Args:
            module_name: Name of the module being transformed
            filename: Path to the file being transformed
        """
        self.module_name = module_name
        self.filename = filename
        self.has_changes = False
        self.function_stack = []  # Track function nesting
    
    def _create_instrumentation_call(self, function_name: str) -> ast.Expr:
        """Create an AST node for the instrumentation call.
        
        Args:
            function_name: Name of the function being instrumented
        
        Returns:
            An AST expression node for the instrumentation call
        """
        # Get the qualified name based on nesting level
        if self.function_stack:
            # For nested functions, include the parent function name
            qualified_name = '.'.join(self.function_stack) + '.' + function_name
        else:
            qualified_name = function_name
            
        # Create instrumentation call to log the function call
        # This creates: function_call_queue.put(FunctionCallEvent(func_name, module_name, filename))
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='function_call_queue', ctx=ast.Load()),
                    attr='put',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Call(
                        func=ast.Name(id='FunctionCallEvent', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=qualified_name),
                            ast.Constant(value=self.module_name),
                            ast.Constant(value=self.filename)
                        ],
                        keywords=[]
                    )
                ],
                keywords=[]
            )
        )
    
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Visit class definitions to track class context.
        
        This helps with identifying method names in their class context.
        
        Args:
            node: The class definition node
        
        Returns:
            The transformed class definition node
        """
        # Process the class body, which may contain methods
        self.generic_visit(node)
        return node
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit and transform function definitions.
        
        Wrap function bodies with instrumentation code that logs function calls.
        Handles nested functions by maintaining a stack of function names.
        
        Args:
            node: The function definition node
        
        Returns:
            The transformed function definition node
        """
        # Save the current function name on the stack
        self.function_stack.append(node.name)
        
        # Process nested functions first
        self.generic_visit(node)
        
        # Create instrumentation call
        func_event = self._create_instrumentation_call(node.name)
        
        # Insert the instrumentation call at the beginning of the function body
        node.body.insert(0, func_event)
        self.has_changes = True
        
        # Remove the function name from the stack
        self.function_stack.pop()
        
        return node
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Visit and transform async function definitions.
        
        Wrap async function bodies with instrumentation code that logs function calls.
        
        Args:
            node: The async function definition node
        
        Returns:
            The transformed async function definition node
        """
        # Use the same approach as for regular functions
        self.function_stack.append(node.name)
        self.generic_visit(node)
        
        func_event = self._create_instrumentation_call(node.name)
        node.body.insert(0, func_event)
        self.has_changes = True
        
        self.function_stack.pop()
        return node
    
    def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
        """Visit lambda functions.
        
        We can't easily instrument lambdas because they're expressions without
        a body block, but we still visit them to find any other functions inside.
        
        Args:
            node: The lambda node
        
        Returns:
            The unchanged lambda node
        """
        self.generic_visit(node)
        return node


class TransformationCache:
    """Cache for transformed Python code to avoid redundant AST transformations."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the transformation cache.
        
        Args:
            cache_dir: Directory to store cached transformations (default: .instrumentation_cache)
        """
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".instrumentation_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache = {}  # In-memory cache for faster lookups
        
    def get_cache_key(self, filename: str, source_code: str) -> str:
        """Generate a unique cache key for a file and its contents.
        
        Args:
            filename: Path to the source file
            source_code: Source code content
            
        Returns:
            A unique cache key
        """
        # Use filename and content hash to create a unique key
        content_hash = hashlib.md5(source_code.encode('utf-8')).hexdigest()
        # Use the module name as part of the key to avoid collisions
        module_name = os.path.basename(filename).split('.')[0]
        return f"{module_name}_{content_hash}"
    
    def get_cache_path(self, cache_key: str) -> str:
        """Get the path for a cached transformation.
        
        Args:
            cache_key: The cache key
            
        Returns:
            Path to the cache file
        """
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    def get(self, filename: str, source_code: str) -> Optional[str]:
        """Get cached transformed code if available.
        
        Args:
            filename: Path to the source file
            source_code: Source code content
            
        Returns:
            Cached transformed code or None if not available
        """
        cache_key = self.get_cache_key(filename, source_code)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            logger.debug(f"In-memory cache hit for {filename}")
            return self.memory_cache[cache_key]
        
        # Check disk cache
        cache_path = self.get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    
                # Update memory cache
                self.memory_cache[cache_key] = cached_data
                
                logger.debug(f"Disk cache hit for {filename}")
                return cached_data
            except Exception as e:
                logger.warning(f"Error loading cache for {filename}: {e}")
        
        return None
    
    def put(self, filename: str, source_code: str, transformed_code: str) -> None:
        """Store transformed code in the cache.
        
        Args:
            filename: Path to the source file
            source_code: Original source code
            transformed_code: Transformed source code
        """
        cache_key = self.get_cache_key(filename, source_code)
        
        # Update memory cache
        self.memory_cache[cache_key] = transformed_code
        
        # Update disk cache
        cache_path = self.get_cache_path(cache_key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(transformed_code, f)
            logger.debug(f"Cached transformation for {filename}")
        except Exception as e:
            logger.warning(f"Error caching transformation for {filename}: {e}")
    
    def invalidate(self, filename: str) -> None:
        """Invalidate cache entries for a file.
        
        Args:
            filename: Path to the source file
        """
        # Since we use content hash, we don't need to explicitly invalidate
        # entries when the file changes. When the content changes, the hash
        # changes, resulting in a different cache key.
        pass
    
    def clear(self) -> None:
        """Clear all cached transformations."""
        self.memory_cache.clear()
        
        # Remove all files in the cache directory
        for file in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, file)
            try:
                if os.path.isfile(file_path) and file.endswith('.pkl'):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Error removing cache file {file_path}: {e}")


class PythonInstrumenter:
    """Class to handle Python code instrumentation."""
    
    def __init__(self, 
                 watch_dir: str, 
                 exclude_patterns: Optional[List[str]] = None,
                 include_patterns: Optional[List[str]] = None,
                 cache_dir: Optional[str] = None):
        """Initialize the instrumenter.
        
        Args:
            watch_dir: Directory to monitor for Python files
            exclude_patterns: List of regex patterns for modules to exclude from instrumentation
            include_patterns: List of regex patterns for modules to include in instrumentation
            cache_dir: Directory to store cached transformations
        """
        self.watch_dir = os.path.abspath(watch_dir)
        
        # Compile regex patterns for module filtering
        self.exclude_patterns = [re.compile(p) for p in exclude_patterns] if exclude_patterns else []
        self.include_patterns = [re.compile(p) for p in include_patterns] if include_patterns else []
        
        # Initialize the transformation cache
        self.cache = TransformationCache(cache_dir)
        
        logger.info(f"Initialized instrumenter to watch {self.watch_dir}")
        if self.exclude_patterns:
            logger.info(f"Excluding modules matching: {exclude_patterns}")
        if self.include_patterns:
            logger.info(f"Including only modules matching: {include_patterns}")
    
    def should_instrument(self, filename: str) -> bool:
        """Determine if a file should be instrumented.
        
        Args:
            filename: Path to the file
        
        Returns:
            True if the file should be instrumented, False otherwise
        """
        if not filename.endswith('.py'):
            return False
        
        abs_path = os.path.abspath(filename)
        
        # Check if file is in the watch directory
        if not abs_path.startswith(self.watch_dir):
            return False
        
        # Convert filepath to module name for pattern matching
        rel_path = os.path.relpath(abs_path, self.watch_dir)
        module_path = rel_path.replace(os.path.sep, '.')
        if module_path.endswith('.py'):
            module_path = module_path[:-3]  # Remove .py extension
        
        # Skip if the module matches any exclude pattern
        for pattern in self.exclude_patterns:
            if pattern.search(module_path) or pattern.search(abs_path):
                logger.debug(f"Skipping {filename} (matches exclude pattern)")
                return False
        
        # If include patterns exist, only instrument if the module matches one
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.search(module_path) or pattern.search(abs_path):
                    return True
            logger.debug(f"Skipping {filename} (doesn't match any include pattern)")
            return False
        
        return True
    
    def instrument_code(self, source_code: str, module_name: str, filename: str) -> str:
        """Instrument Python source code.
        
        Args:
            source_code: The source code to instrument
            module_name: The name of the module
            filename: Path to the file
        
        Returns:
            The instrumented source code
        """
        # Check if we should instrument this module
        if not self.should_instrument(filename):
            return source_code
        
        # Check if we have cached transformed code
        cached_code = self.cache.get(filename, source_code)
        if cached_code is not None:
            # Track this file as being monitored
            with _lock:
                monitored_files.add(filename)
            return cached_code
        
        try:
            tree = ast.parse(source_code)
            transformer = InstrumentationTransformer(module_name, filename)
            transformed_tree = transformer.visit(tree)
            
            if transformer.has_changes:
                # Add imports for the instrumentation
                imports = ast.parse(
                    "from graph_core.dynamic.import_hook import function_call_queue, FunctionCallEvent"
                ).body
                transformed_tree.body.insert(0, imports[0])
                
                # Fix line numbers
                ast.fix_missing_locations(transformed_tree)
                
                # Track this file as being monitored
                with _lock:
                    monitored_files.add(filename)
                
                logger.info(f"Instrumented {module_name} in {filename}")
                
                # Convert back to source code
                instrumented_code = ast.unparse(transformed_tree)
                
                # Cache the transformed code
                self.cache.put(filename, source_code, instrumented_code)
                
                return instrumented_code
            else:
                # No functions to instrument
                logger.debug(f"No functions to instrument in {module_name}")
                return source_code
        except SyntaxError as e:
            logger.error(f"Syntax error in {filename}: {e}")
            return source_code
        except Exception as e:
            logger.error(f"Error instrumenting {filename}: {e}")
            return source_code


class InstrumentationFinder(importlib.abc.MetaPathFinder):
    """Custom meta path finder for instrumenting Python modules."""
    
    def __init__(self, instrumenter: PythonInstrumenter):
        """Initialize the finder.
        
        Args:
            instrumenter: The instrumenter to use
        """
        self.instrumenter = instrumenter
        # Cache for specs being processed to prevent recursion
        self._processing = set()
    
    def find_spec(self, fullname: str, path: Optional[List[str]], target: Optional[Any] = None) -> Optional[importlib.machinery.ModuleSpec]:
        """Find and create a module spec with instrumentation.
        
        Args:
            fullname: The fully qualified name of the module
            path: The path to search for the module
            target: The target module
        
        Returns:
            A module spec or None if the module can't be found
        """
        # Prevent recursion by tracking modules being processed
        if fullname in self._processing:
            return None
        
        # Skip standard library modules and our own modules
        if (fullname.startswith('_') or 
            fullname.startswith('graph_core.dynamic') or
            fullname.startswith('importlib') or
            '.' in fullname and fullname.split('.')[0] in sys.builtin_module_names):
            return None
        
        try:
            # Add to processing set to prevent recursion
            self._processing.add(fullname)
            
            # Use importlib.machinery directly to avoid recursive calls
            if path is None:
                path = sys.path
            
            # Try to find the spec with the original method
            for finder in sys.meta_path:
                if finder is self:
                    continue
                try:
                    spec = finder.find_spec(fullname, path, target)
                    if spec is not None:
                        break
                except Exception:
                    continue
            else:
                spec = None
            
            if spec is None or spec.origin is None or not spec.origin.endswith('.py'):
                return spec
            
            # Check if we should instrument this file
            if not self.instrumenter.should_instrument(spec.origin):
                return spec
            
            # Create a custom loader
            loader = InstrumentationLoader(
                spec.loader, self.instrumenter, fullname, spec.origin
            )
            
            # Create a new spec with our loader
            new_spec = importlib.machinery.ModuleSpec(
                name=fullname,
                loader=loader,
                origin=spec.origin,
                is_package=spec.submodule_search_locations is not None
            )
            
            # Add submodule_search_locations if it exists
            if spec.submodule_search_locations is not None:
                new_spec.submodule_search_locations = spec.submodule_search_locations
            
            return new_spec
        finally:
            # Always remove from processing set
            self._processing.discard(fullname)


class InstrumentationLoader(importlib.abc.Loader):
    """Custom loader that instruments Python code during import."""
    
    def __init__(self, original_loader: importlib.abc.Loader, instrumenter: PythonInstrumenter, 
                 fullname: str, filename: str):
        """Initialize the loader.
        
        Args:
            original_loader: The original module loader
            instrumenter: The instrumenter to use
            fullname: The fully qualified name of the module
            filename: Path to the file
        """
        self.original_loader = original_loader
        self.instrumenter = instrumenter
        self.fullname = fullname
        self.filename = filename
    
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> Optional[types.ModuleType]:
        """Create a module object.
        
        Args:
            spec: The module spec
        
        Returns:
            The created module or None to use the default
        """
        # Use the original loader's create_module
        if hasattr(self.original_loader, 'create_module'):
            return self.original_loader.create_module(spec)
        return None
    
    def exec_module(self, module: types.ModuleType) -> None:
        """Execute a module with instrumentation.
        
        Args:
            module: The module to execute
        """
        # Get the source code
        source = self.get_source(self.fullname)
        if source is None:
            # Fall back to the original loader
            if hasattr(self.original_loader, 'exec_module'):
                self.original_loader.exec_module(module)
            else:
                raise ImportError(f"Cannot execute module {self.fullname}")
            return
        
        # Instrument the code
        instrumented_source = self.instrumenter.instrument_code(
            source, self.fullname, self.filename
        )
        
        # Compile the instrumented code
        code = compile(instrumented_source, self.filename, 'exec')
        
        # Execute the code in the module's namespace
        exec(code, module.__dict__)
    
    def get_source(self, name: str) -> Optional[str]:
        """Get the source code for a module.
        
        Args:
            name: The name of the module
        
        Returns:
            The source code or None if not available
        """
        if hasattr(self.original_loader, 'get_source'):
            return self.original_loader.get_source(name)
        return None


def initialize_hook(
    watch_dir: str = 'src',
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    cache_dir: Optional[str] = None
) -> None:
    """Initialize and install the import hook.
    
    Args:
        watch_dir: Directory to monitor for Python files (default: 'src')
        exclude_patterns: List of regex patterns for modules to exclude from instrumentation
        include_patterns: List of regex patterns for modules to include in instrumentation
        cache_dir: Directory to store cached transformations
    """
    watch_dir = os.path.abspath(watch_dir)
    logger.info(f"Initializing import hook to watch {watch_dir}")
    
    # Create the instrumenter with filtering and caching
    instrumenter = PythonInstrumenter(
        watch_dir,
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
        cache_dir=cache_dir
    )
    
    # Create and install the finder
    finder = InstrumentationFinder(instrumenter)
    sys.meta_path.insert(0, finder)
    
    logger.info("Import hook installed")
    return finder


def get_function_calls(timeout: Optional[float] = 0.1) -> List[FunctionCallEvent]:
    """Get all function call events from the queue.
    
    Args:
        timeout: Timeout in seconds for getting events (default: 0.1)
    
    Returns:
        List of function call events
    """
    events = []
    try:
        while True:
            event = function_call_queue.get(block=False)
            events.append(event)
    except queue.Empty:
        pass
    
    return events


def get_monitored_files() -> Set[str]:
    """Get the set of monitored files.
    
    Returns:
        Set of monitored file paths
    """
    with _lock:
        return set(monitored_files)


def clear_call_queue() -> None:
    """Clear the function call queue."""
    try:
        while True:
            function_call_queue.get(block=False)
    except queue.Empty:
        pass


def clear_transformation_cache(cache_dir: Optional[str] = None) -> None:
    """Clear the transformation cache.
    
    Args:
        cache_dir: Directory containing the cache
    """
    cache = TransformationCache(cache_dir)
    cache.clear()
    logger.info("Transformation cache cleared") 