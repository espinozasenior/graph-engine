#!/usr/bin/env python
"""
Script to build Tree-sitter language libraries.

This script clones and builds Tree-sitter grammar repositories for supported languages,
then copies the compiled libraries to the appropriate location.
"""
import os
import sys
import shutil
import subprocess
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Supported languages and their repositories
LANGUAGES = {
    'python': 'https://github.com/tree-sitter/tree-sitter-python',
    'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
    'typescript': 'https://github.com/tree-sitter/tree-sitter-typescript',
}


def run_command(cmd: List[str], cwd: Optional[str] = None) -> bool:
    """
    Run a shell command and return whether it succeeded.
    
    Args:
        cmd: The command to run as a list of strings
        cwd: The directory to run the command in
        
    Returns:
        True if the command succeeded, False otherwise
    """
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(
            cmd,
            check=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        return False


def clone_repo(url: str, target_dir: str) -> bool:
    """
    Clone a git repository.
    
    Args:
        url: The URL of the repository
        target_dir: The directory to clone into
        
    Returns:
        True if cloning succeeded, False otherwise
    """
    if os.path.exists(target_dir):
        logger.info(f"Repository already exists at {target_dir}")
        return True
    
    return run_command(['git', 'clone', url, target_dir])


def build_with_tree_sitter_cli(repo_dir: str) -> bool:
    """
    Build a Tree-sitter grammar using the tree-sitter CLI.
    
    Args:
        repo_dir: The directory containing the grammar repository
        
    Returns:
        True if building succeeded, False otherwise
    """
    # Generate the grammar
    if not run_command(['tree-sitter', 'generate'], cwd=repo_dir):
        return False
    
    # Build the parser
    if not run_command(['tree-sitter', 'build-wasm'], cwd=repo_dir):
        return False
    
    return True


def build_with_python_lib(repo_dir: str, language_name: str, output_file: str) -> bool:
    """
    Build a Tree-sitter grammar using the Python tree-sitter library.
    
    Args:
        repo_dir: The directory containing the grammar repository
        language_name: The name of the language
        output_file: The path to the output .so file
        
    Returns:
        True if building succeeded, False otherwise
    """
    try:
        from tree_sitter import Language
        
        Language.build_library(output_file, [repo_dir])
        logger.info(f"Successfully built {language_name} grammar at {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to build {language_name} grammar: {str(e)}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Build Tree-sitter language libraries')
    parser.add_argument(
        '--languages', 
        nargs='+', 
        choices=list(LANGUAGES.keys()) + ['all'],
        default=['all'],
        help='Languages to build (or "all")'
    )
    parser.add_argument(
        '--method',
        choices=['cli', 'python'],
        default='python',
        help='Method to build the grammars (cli or python)'
    )
    parser.add_argument(
        '--repo-dir',
        type=str,
        default='build_tmp',
        help='Directory to clone repositories into'
    )
    
    args = parser.parse_args()
    
    # Determine which languages to build
    languages_to_build = list(LANGUAGES.keys()) if 'all' in args.languages else args.languages
    
    # Create output directory
    curr_dir = Path(__file__).parent
    output_dir = curr_dir / 'languages'
    os.makedirs(output_dir, exist_ok=True)
    
    # Create temp directory for repos
    temp_dir = curr_dir / args.repo_dir
    os.makedirs(temp_dir, exist_ok=True)
    
    # Build each language
    success_count = 0
    for language in languages_to_build:
        logger.info(f"Building {language} grammar...")
        repo_url = LANGUAGES[language]
        repo_dir = temp_dir / f"tree-sitter-{language}"
        
        # Handle TypeScript special case
        if language == 'typescript':
            repo_dir = temp_dir / "tree-sitter-typescript"
            language_dir = repo_dir / language
        else:
            language_dir = repo_dir
        
        # Clone repository
        if not clone_repo(repo_url, str(repo_dir)):
            logger.error(f"Failed to clone {language} repository")
            continue
        
        # Build grammar
        output_file = output_dir / f"{language}.so"
        
        if args.method == 'cli':
            if build_with_tree_sitter_cli(str(language_dir)):
                # Copy the built parser
                wasm_file = language_dir / 'build' / f"{language}.wasm"
                
                if wasm_file.exists():
                    shutil.copy(str(wasm_file), str(output_file))
                    logger.info(f"Copied {language} grammar to {output_file}")
                    success_count += 1
                else:
                    logger.error(f"Could not find built {language} grammar at {wasm_file}")
            else:
                logger.error(f"Failed to build {language} grammar with tree-sitter CLI")
        else:  # python method
            if build_with_python_lib(str(language_dir), language, str(output_file)):
                success_count += 1
            else:
                logger.error(f"Failed to build {language} grammar with Python library")
    
    # Summary
    if success_count == len(languages_to_build):
        logger.info(f"Successfully built all {len(languages_to_build)} language grammars")
    else:
        logger.warning(
            f"Built {success_count} out of {len(languages_to_build)} language grammars"
        )


if __name__ == '__main__':
    main() 