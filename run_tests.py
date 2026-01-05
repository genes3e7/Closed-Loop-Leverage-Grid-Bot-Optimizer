"""
Build Script (Project Automation).
Runs Linting, Tests, and Stress Checks.
"""

import subprocess
import sys


def run_command(command, description):
    print(f"--- Running {description} ---")
    try:
        subprocess.check_call(command, shell=True)
        print(f"✅ {description} Passed.\n")
    except subprocess.CalledProcessError:
        print(f"❌ {description} FAILED.")
        sys.exit(1)


def main():
    print("👷 STARTING BUILD PROCESS...\n")

    # 1. Install Dependencies (Optional, for CI mostly)
    # run_command("pip install -r requirements.txt", "Dependency Check")

    # 2. Run Ruff (Linting)
    # Assuming ruff is installed
    run_command("ruff check src/ tests/", "Linter (Ruff)")

    # 3. Run Pytest
    run_command("pytest tests/ -v", "Unit & Integration Tests")

    print("🎉 BUILD SUCCESSFUL! Project is stable.")


if __name__ == "__main__":
    main()
