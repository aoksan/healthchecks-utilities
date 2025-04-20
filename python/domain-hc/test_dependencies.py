#!/usr/bin/env python3
"""
Test script to verify that all required dependencies are installed.
"""
import sys

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = ['requests', 'dotenv']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is NOT installed")

    if missing_packages:
        print("\nMissing packages. Please install them using one of the following methods:")
        print("\nUsing pip with requirements.txt:")
        print("  pip install -r requirements.txt")
        print("\nUsing pip with pyproject.toml (requires pip >= 21.3):")
        print("  pip install -e .")
        return False
    else:
        print("\nAll dependencies are installed correctly!")
        return True

if __name__ == "__main__":
    print("Checking dependencies for Healthchecks Utilities...\n")
    success = check_dependencies()
    sys.exit(0 if success else 1)
