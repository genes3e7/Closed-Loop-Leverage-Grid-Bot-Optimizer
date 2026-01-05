"""
Script to compile the project into a standalone executable using PyInstaller.
"""

import subprocess
import sys
import shutil
import os


def check_pyinstaller():
    """Checks if PyInstaller is installed."""
    try:
        import PyInstaller

        print("✅ PyInstaller is installed.")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build():
    print("\n🔨 Building Executable...")

    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("GridOptimizer.spec"):
        os.remove("GridOptimizer.spec")

    # PyInstaller Command
    # --onefile: Bundle everything into a single .exe
    # --name: Name of the output file
    # --add-data: (Optional) If you had config files, you'd add them here.
    # main.py: Your entry point

    command = ["pyinstaller", "--onefile", "--name=GridOptimizer", "--clean", "main.py"]

    try:
        subprocess.check_call(command, shell=True)
        print("\n🎉 Build Success! Executable is located at: dist/GridOptimizer.exe")
    except subprocess.CalledProcessError:
        print("\n❌ Build Failed.")


if __name__ == "__main__":
    check_pyinstaller()
    build()
