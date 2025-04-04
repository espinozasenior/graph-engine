import subprocess
import sys
import os
import pytest

# Ensure the commands run from the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pytest.mark.skipif(sys.platform == "win32", reason="Test runner differences on Windows")
def test_coverage_report_generation():
    """Tests if the pytest coverage command runs without errors."""
    # Use sys.executable to ensure the correct python interpreter is used
    command = [
        sys.executable, '-m', 'pytest', 
        '--cov=graph_core', 
        '--cov-report=html', 
        '-p', 'no:terminal' # Disable terminal reporting for cleaner execution
    ]
    
    # Run the command from the project root
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    
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
    command = [
        sys.executable, 
        os.path.join(PROJECT_ROOT, 'run_graph_manager.py'),
        '--src-dir', os.path.join(PROJECT_ROOT, 'src'), 
        '--output', output_file
    ]
    
    # Run the command from the project root
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    
    # Assert command completed successfully
    assert result.returncode == 0, f"Snapshot generation command failed with exit code {result.returncode}\nStderr: {result.stderr}\nStdout: {result.stdout}"
    # Optionally, check if the output file was created
    assert os.path.exists(output_file), f"Snapshot file {output_file} not found."
    
    # Clean up the generated file
    if os.path.exists(output_file):
        os.remove(output_file)

# You might need to add setup/teardown fixtures if the tests require specific
# file structures or environment states. 