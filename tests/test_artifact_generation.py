import subprocess
import sys
import os
import pytest

# Ensure the commands run from the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Check if running in CI environment
IN_CI = os.environ.get("CI", "false").lower() == "true"

@pytest.mark.skipif(sys.platform == "win32" or IN_CI, 
                    reason="Test runner differences on Windows or running in CI environment")
def test_coverage_report_generation():
    """Tests if the pytest coverage command runs without errors."""
    # Use sys.executable to ensure the correct python interpreter is used
    command = [
        sys.executable, '-m', 'pytest', 
        '--cov=graph_core', 
        '--cov-report=html', 
        '-p', 'no:terminal' # Disable terminal reporting for cleaner execution
    ]
    
    # Run the command from the project root with a timeout
    try:
        result = subprocess.run(
            command, 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True, 
            timeout=300 # Add a 5-minute timeout
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Coverage command timed out after 300 seconds.\nStdout: {e.stdout}\nStderr: {e.stderr}")

    # Assert that the command completed successfully (exit code 0)
    # Allow exit code 5 (no tests collected) if that's a possibility, 
    # as we only care about the command running without *crashing*.
    assert result.returncode in [0, 5], f"Coverage command failed with exit code {result.returncode}\nStderr: {result.stderr}\nStdout: {result.stdout}"
    # Optionally, check if the htmlcov directory or index.html was created
    assert os.path.exists(os.path.join(PROJECT_ROOT, 'htmlcov', 'index.html')), "Coverage report index.html not found."

@pytest.mark.skipif(sys.platform == "win32", reason="Test runner differences on Windows")
def test_graph_snapshot_generation():
    """Tests if the graph snapshot generation command runs without errors."""
    # Define the command to run the graph manager script
    # This assumes run_graph_manager.py is executable and in the root
    # Adjust path and arguments if necessary
    output_file = os.path.join(PROJECT_ROOT, 'test_graph_snapshot.json')
    
    # Create a simple script that uses the DependencyGraphManager to generate a snapshot
    temp_script_path = os.path.join(PROJECT_ROOT, 'temp_snapshot.py')
    with open(temp_script_path, 'w') as f:
        f.write("""
import os
import sys
import json
from graph_core.manager import DependencyGraphManager

def main():
    # Get command line arguments
    if len(sys.argv) < 3:
        print("Usage: python temp_snapshot.py <src_dir> <output_file>")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    # Create a manager with in-memory storage
    manager = DependencyGraphManager()
    
    # Process existing files
    manager.process_existing_files(src_dir)
    
    # Get all nodes and edges
    nodes = manager.storage.get_all_nodes()
    edges = manager.storage.get_all_edges()
    
    # Create the snapshot
    snapshot = {
        'nodes': [dict(node) for node in nodes],
        'edges': [dict(edge) for edge in edges]
    }
    
    # Write to output file
    with open(output_file, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"Snapshot written to {output_file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
""")
    
    # Run the temporary script instead
    command = [
        sys.executable,
        temp_script_path,
        os.path.join(PROJECT_ROOT, 'src'),
        output_file
    ]
    
    try:
        # Run the command
        result = subprocess.run(
            command, 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True, 
            timeout=300 # Add a 5-minute timeout
        )
    except subprocess.TimeoutExpired as e:
         pytest.fail(f"Snapshot generation command timed out after 300 seconds.\nStdout: {e.stdout}\nStderr: {e.stderr}")
    finally:
        # Clean up the temporary script
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

    # Assert command completed successfully
    assert result.returncode == 0, f"Snapshot generation command failed with exit code {result.returncode}\nStderr: {result.stderr}\nStdout: {result.stdout}"
    # Optionally, check if the output file was created
    assert os.path.exists(output_file), f"Snapshot file {output_file} not found."
    
    # Clean up the generated file
    if os.path.exists(output_file):
        os.remove(output_file)

# You might need to add setup/teardown fixtures if the tests require specific
# file structures or environment states. 