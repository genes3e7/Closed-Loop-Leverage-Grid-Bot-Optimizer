"""
Tests for the CLI entry point (main.py).
Ensures arguments are parsed correctly.
"""

import subprocess
import sys


def test_main_help_command():
    """Ensure -h works and returns exit code 0."""
    result = subprocess.run([sys.executable, "main.py", "-h"], capture_output=True)
    assert result.returncode == 0
    assert b"Closed Loop Grid Bot Optimizer" in result.stdout


def test_main_basic_run():
    """
    Runs the actual main.py with a mocked controller.
    This ensures the argparse logic connects to the controller logic.
    """
    code = """
import sys
import os
from unittest.mock import patch

# Ensure CWD is in path so we can import 'main'
sys.path.insert(0, os.getcwd())

import main

# CRITICAL FIX: Patch 'main.run_analysis' instead of 'src.controller.run_analysis'.
# main.py does "from src.controller import run_analysis".
# This binds the function to the 'main' namespace at import time.
# Patching the original source location won't update the reference in 'main'.
# We must patch where it is USED.
with patch('main.run_analysis') as mock_run:
    # Scenario: Run WITHOUT specifying --portfolio.
    # Expectation: portfolio arg should be passed as None to controller.
    # Note: is_neutral defaults to False in argparse.
    sys.argv = ['main.py', 'BTC', '--days', '5']
    main.main()
    mock_run.assert_called_with(ticker='BTC', exchange='binance', days=5, portfolio=None, is_neutral=False)
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )

    if result.returncode != 0:
        print("Subprocess Error Output:")
        print(result.stderr)

    assert result.returncode == 0
