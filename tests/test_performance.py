"""
Tests for the performance profiler script.
"""

import os
import sys
import tempfile
import unittest
import subprocess
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Assuming profiler.py is in performance/ directory
PROFILER_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "performance", "profiler.py"))

class TestPerformanceProfiler(unittest.TestCase):
    """Tests for the performance/profiler.py script."""

    def setUp(self):
        """Set up a temporary directory with sample files."""
        self.temp_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(self.src_dir)

        # Create dummy Python files
        with open(os.path.join(self.src_dir, "file1.py"), "w") as f:
            f.write("def func1():\\n    pass\\n")
        with open(os.path.join(self.src_dir, "file2.py"), "w") as f:
            f.write("import os\\n\\ndef func2(a, b):\\n    return a + b\\n")
        # Add a file with a potential (but excluded) secret
        with open(os.path.join(self.src_dir, "config.py"), "w") as f:
            f.write("API_KEY = 'YOUR_API_KEY_HERE' # Placeholder\\n")

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_profiler_runs_and_reports(self):
        """Test that the profiler script runs and produces a report."""
        # Ensure the script exists
        self.assertTrue(os.path.exists(PROFILER_SCRIPT_PATH), f"Profiler script not found at {PROFILER_SCRIPT_PATH}")

        # Run the profiler script as a subprocess
        try:
            result = subprocess.run(
                [sys.executable, PROFILER_SCRIPT_PATH, self.src_dir, "--storage", "memory"],
                capture_output=True,
                text=True,
                check=True, # Raise exception on non-zero exit code
                encoding='utf-8'
            )
        except subprocess.CalledProcessError as e:
            print("Profiler script failed:")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            self.fail(f"Profiler script execution failed with code {e.returncode}")

        # Check the output
        output = result.stdout
        print("Profiler Output:\n", output) # Print output for debugging

        self.assertIn("--- Performance Report ---", output)
        self.assertIn("Overall processing time:", output)
        self.assertIn("Step", output) # Header check
        self.assertIn("Total Time (s)", output) # Header check
        self.assertIn("parse_file", output) # Check if parsing was timed
        self.assertIn("scan_secrets", output) # Check if secret scanning was timed
        # Check memory storage update timing (specific name used in profiler)
        self.assertIn("storage_add_update_memory", output)

    def test_profiler_json_storage(self):
        """Test the profiler script with JSON storage."""
        json_path = os.path.join(self.temp_dir, "test_profile.json")

        # Run the profiler script with JSON storage
        try:
            result = subprocess.run(
                [sys.executable, PROFILER_SCRIPT_PATH, self.src_dir, "--storage", "json", "--json-path", json_path],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
        except subprocess.CalledProcessError as e:
            print("Profiler script (JSON) failed:")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            self.fail(f"Profiler script (JSON) execution failed with code {e.returncode}")

        # Check the output
        output = result.stdout
        print("Profiler Output (JSON):\n", output)

        self.assertIn("--- Performance Report ---", output)
        self.assertIn("parse_file", output)
        self.assertIn("scan_secrets", output)
        # Check JSON storage timing (specific names used in profiler)
        self.assertIn("storage_add_update_json", output)
        self.assertIn("storage_save_json", output)
        self.assertTrue(os.path.exists(json_path), "JSON output file was not created")

if __name__ == '__main__':
    unittest.main()