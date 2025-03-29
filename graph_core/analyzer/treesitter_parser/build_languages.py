#!/usr/bin/env python3
"""
Script to build Tree-sitter language grammar files.

This script clones the required Tree-sitter repositories and builds the language
grammars needed by the TreeSitterParser.
"""

import os
import sys
import shutil
import argparse
import subprocess
import logging
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Supported languages and their repositories
LANGUAGES = {
    'python': 'https://github.com/tree-sitter/tree-sitter-python',
    'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
    'typescript': 'https://github.com/tree-sitter/tree-sitter-typescript'
}

# Path for storing the compiled language libraries
LANGUAGE_DIR = Path(__file__).parent / 'languages'


def ensure_dir_exists(path):
    """Ensure the directory exists, creating it if needed."""
    path.mkdir(parents=True, exist_ok=True)


def clone_repo(lang, repo_url):
    """
    Clone a repository if it doesn't exist.
    
    Args:
        lang: The language name
        repo_url: The URL of the repository to clone
        
    Returns:
        Path to the cloned repository
    """
    # Use a temporary directory for cloning
    repo_dir = Path(tempfile.gettempdir()) / f"tree-sitter-{lang}"
    
    if repo_dir.exists():
        logger.info(f"Repository already exists at {repo_dir}")
        return repo_dir
        
    try:
        logger.info(f"Cloning {repo_url} to {repo_dir}")
        subprocess.run(
            ['git', 'clone', repo_url, str(repo_dir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return repo_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {str(e)}")
        logger.error(f"Error output: {e.stderr.decode()}")
        return None


def build_with_gcc(lang, repo_dir):
    """
    Build the language grammar using gcc directly.
    
    Args:
        lang: The language name
        repo_dir: Path to the repository
        
    Returns:
        True if build was successful, False otherwise
    """
    try:
        src_path = repo_dir / 'src'
        
        # Special case for TypeScript which has nested parser directories
        if lang == 'typescript':
            src_path = repo_dir / 'typescript' / 'src'
            
            # Attempt to run npm install in the TypeScript directory
            try:
                logger.info("Running npm install for TypeScript parser")
                subprocess.run(
                    ['npm', 'install'],
                    cwd=str(repo_dir),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"npm install failed: {str(e)}")
                logger.warning("Continuing with build anyway...")
        
        # Output file path
        output_file = LANGUAGE_DIR / f"{lang}.so"
        
        # Source files
        parser_files = list(src_path.glob("*.c"))
        
        if not parser_files:
            logger.error(f"No C source files found in {src_path}")
            return False
            
        # Common source files from tree-sitter
        scanner_file = src_path / "scanner.c"
        
        # Compile command
        gcc_args = [
            'gcc', '-shared', '-fPIC', '-g', '-O2',
            '-I', str(repo_dir / 'src'),
        ]
        
        # Add source files
        for file in parser_files:
            gcc_args.append(str(file))
            
        # Add scanner if it exists
        if scanner_file.exists():
            gcc_args.append(str(scanner_file))
            
        # Add output file
        gcc_args.extend(['-o', str(output_file)])
        
        # Run gcc
        logger.info(f"Building {lang} grammar with gcc")
        logger.debug(f"Command: {' '.join(gcc_args)}")
        
        result = subprocess.run(
            gcc_args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Successfully built {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to build {lang} grammar with gcc")
        logger.error(f"Error output: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error building {lang} grammar: {str(e)}")
        return False


def main():
    """Main function to build the language grammars."""
    parser = argparse.ArgumentParser(description='Build Tree-sitter language grammars')
    parser.add_argument('--method', choices=['gcc'], default='gcc',
                        help='Method to use for building the language grammars')
    parser.add_argument('--languages', nargs='+', choices=list(LANGUAGES.keys()),
                        default=list(LANGUAGES.keys()),
                        help='Languages to build (default: all)')
    args = parser.parse_args()
    
    # Create the language directory
    ensure_dir_exists(LANGUAGE_DIR)
    
    # Build each language
    success_count = 0
    
    for lang in args.languages:
        logger.info(f"Building {lang} grammar")
        
        # Clone the repository
        repo_dir = clone_repo(lang, LANGUAGES[lang])
        if not repo_dir:
            logger.error(f"Failed to clone repository for {lang}")
            continue
            
        # Build the language grammar
        if args.method == 'gcc':
            if build_with_gcc(lang, repo_dir):
                success_count += 1
    
    # Report results
    if success_count == len(args.languages):
        logger.info(f"Successfully built all {success_count} language grammars")
    else:
        logger.warning(f"Built {success_count} out of {len(args.languages)} language grammars")


if __name__ == "__main__":
    main() 