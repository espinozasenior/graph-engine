"""
Performance Profiling Script for Dependency Graph Manager

This script processes a directory of code files using the DependencyGraphManager
and measures the time spent in key stages like parsing, secret scanning, and storage.
"""

import os
import time
import logging
import argparse
from collections import defaultdict
from typing import Dict, List, Any, Callable
import functools

# Ensure the graph_core package is findable
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph_core.manager import DependencyGraphManager
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage
from graph_core.analyzer.treesitter_parser.tree_sitter_parser import TreeSitterParser
from graph_core.security.graph_integration import scan_parse_result_for_secrets

# Set up logging
logger = logging.getLogger(__name__)

# --- Profiling Setup ---

TIMINGS: Dict[str, List[float]] = defaultdict(list)

def time_it(name: str) -> Callable:
    """Decorator to measure execution time of a function and store it."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            duration = end_time - start_time
            TIMINGS[name].append(duration)
            # logger.debug(f"'{name}' took {duration:.6f}s")
            return result
        return wrapper
    return decorator

# --- Main Profiling Logic ---

def profile_directory(directory: str, storage_type: str = "memory", json_path: str = None) -> None:
    """
    Profiles the processing of a directory.

    Args:
        directory: The directory path containing code files.
        storage_type: 'memory' or 'json'.
        json_path: Path for JSON storage (if used).
    """
    logger.info(f"Starting profiling for directory: {directory} using {storage_type} storage.")
    global TIMINGS
    TIMINGS.clear()

    # --- Apply Timing Decorators (Monkey Patching) ---
    original_methods = {}

    def patch_method(cls, method_name, timing_name):
        if hasattr(cls, method_name):
            original = getattr(cls, method_name)
            decorated = time_it(timing_name)(original)
            setattr(cls, method_name, decorated)
            original_methods[(cls, method_name)] = original
            # logger.debug(f"Patched {cls.__name__}.{method_name} for timing as '{timing_name}'")
        else:
            logger.warning(f"Method {method_name} not found on {cls.__name__} for patching.")

    try:
        # Patch key methods
        patch_method(TreeSitterParser, 'parse_file', 'parse_file')
        patch_method(JSONGraphStorage, 'add_or_update_file', 'storage_add_update_json')
        patch_method(JSONGraphStorage, 'save_graph', 'storage_save_json')
        patch_method(InMemoryGraphStorage, 'add_or_update_file', 'storage_add_update_memory')
        # Patching the function directly as it's not a method of a commonly instantiated class here
        # Note: This requires careful handling if the function is imported differently elsewhere
        import graph_core.manager
        original_scan_secrets = graph_core.manager.scan_parse_result_for_secrets
        graph_core.manager.scan_parse_result_for_secrets = time_it('scan_secrets')(original_scan_secrets)
        original_methods[(graph_core.manager, 'scan_parse_result_for_secrets')] = original_scan_secrets
        # logger.debug("Patched scan_parse_result_for_secrets for timing as 'scan_secrets'")

        # --- Setup Manager ---
        if storage_type == "json":
            if not json_path:
                json_path = os.path.join(directory, "..", "data", "profiled_graph.json")
            logger.info(f"Using JSON storage at: {json_path}")
            # Clear existing JSON if it exists to get clean run
            if os.path.exists(json_path):
                os.remove(json_path)
            if os.path.exists(json_path + ".lock"):
                 os.remove(json_path + ".lock")
            manager = DependencyGraphManager.create_with_json_storage(json_path)
        else:
            logger.info("Using in-memory storage.")
            manager = DependencyGraphManager.create_with_memory_storage()

        # --- Run Processing ---
        logger.info("Processing existing files...")
        overall_start_time = time.perf_counter()

        processed_count = manager.process_existing_files(directory)

        overall_end_time = time.perf_counter()
        overall_duration = overall_end_time - overall_start_time
        logger.info(f"Finished processing {processed_count} files in {overall_duration:.4f} seconds.")

        # --- Generate Report ---
        print("\n--- Performance Report ---")
        print(f"Overall processing time: {overall_duration:.4f}s for {processed_count} files")
        print("--------------------------")
        print(f"{'Step':<30} | {'Total Time (s)':<15} | {'Calls':<8} | {'Avg Time (ms)':<15}")
        print("-----------------------------------------------------------------------")

        report_data = []
        total_timed_spent = 0
        for name, durations in TIMINGS.items():
            total_time = sum(durations)
            num_calls = len(durations)
            avg_time_ms = (total_time / num_calls * 1000) if num_calls > 0 else 0
            report_data.append({
                'name': name,
                'total': total_time,
                'calls': num_calls,
                'avg_ms': avg_time_ms
            })
            total_timed_spent += total_time

        # Sort by total time descending
        report_data.sort(key=lambda x: x['total'], reverse=True)

        for item in report_data:
            print(f"{item['name']:<30} | {item['total']:<15.4f} | {item['calls']:<8} | {item['avg_ms']:<15.4f}")

        print("-----------------------------------------------------------------------")
        other_time = overall_duration - total_timed_spent
        print(f"Untimed/Overhead: {other_time:.4f}s")
        print("--------------------------\n")

    finally:
        # --- Restore Original Methods ---
        # logger.debug("Restoring original methods...")
        for (cls_or_module, method_name), original in original_methods.items():
            try:
                setattr(cls_or_module, method_name, original)
                # logger.debug(f"Restored {cls_or_module.__name__}.{method_name}")
            except Exception as e:
                 logger.error(f"Failed to restore {method_name} on {cls_or_module}: {e}")
        # Special handling for the function patched directly on the module
        if (graph_core.manager, 'scan_parse_result_for_secrets') in original_methods:
            graph_core.manager.scan_parse_result_for_secrets = original_methods[(graph_core.manager, 'scan_parse_result_for_secrets')]
            # logger.debug("Restored scan_parse_result_for_secrets")


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Profile the dependency graph building process.")
    parser.add_argument("directory", help="Directory containing code files to process.")
    parser.add_argument("--storage", choices=["memory", "json"], default="memory",
                        help="Type of storage to use (default: memory).")
    parser.add_argument("--json-path", default=None,
                        help="Path for JSON storage file (default: ../data/profiled_graph.json relative to target dir).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logging.getLogger('graph_core').setLevel(log_level) # Ensure core logs are also controlled

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found: {args.directory}")
        sys.exit(1)

    profile_directory(args.directory, args.storage, args.json_path)

if __name__ == "__main__":
    main()