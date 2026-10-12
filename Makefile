# Makefile for healthchecks-utilities
# Supported platforms: Linux, macOS, Windows
# Requires: make, uv

.PHONY: help install source lint test clean

# Detect Windows vs Unix
ifeq ($(OS),Windows_NT)
    PLATFORM := windows
else
    PLATFORM := unix
endif

help:
	@echo "Available commands:"
	@echo "  make install   - Create/update the virtual environment and install dependencies using uv"
	@echo "  make source    - Activate the virtual environment"
	@echo "  make lint      - Run the linter"
	@echo "  make test      - Run the unit tests"
	@echo "  make clean     - Clean temporary files and caches"

install:
	@echo "Setting up project with uv..."
	@uv sync --link-mode=copy
	@echo "Project setup complete."

# ---------------------------------------------------------
# Windows-specific commands
# ---------------------------------------------------------
ifeq ($(PLATFORM),windows)

source:
	@echo "To activate the virtual environment in PowerShell, run:"
	@echo ".venv\Scripts\Activate.ps1"
	@echo ""
	@echo "Or in Command Prompt:"
	@echo ".venv\Scripts\activate.bat"

clean:
	@echo "Cleaning up Windows environments..."
	@powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -Recurse -Force .pytest_cache,build,dist,.venv -ErrorAction SilentlyContinue; Get-ChildItem -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue; Get-ChildItem -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@echo "Clean up complete."

# ---------------------------------------------------------
# Unix/macOS-specific commands
# ---------------------------------------------------------
else

source:
	@echo "Activating virtual environment..."
	@bash -c 'source .venv/bin/activate && exec bash'

clean:
	@echo "Cleaning up Unix environments..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache build dist .venv *.egg-info
	@echo "Clean up complete."

endif
# ---------------------------------------------------------

lint:
	@echo "Running linter..."
	@uv run flake8 src

test:
	@echo "Running tests..."
	@uv run pytest -s