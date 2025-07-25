# Makefile for healthchecks-utilities

# Use the user's default shell, defaulting to bash
SHELL := /bin/bash

.PHONY: help lint test clean install source

help:
	@echo "Available commands:"
	@echo "  make install   - Create a virtual environment and install dependencies using Rye"
	@echo "  make source    - Spawn a new shell with the virtual environment activated"
	@echo "  make lint      - Run the linter on the source code using Rye"
	@echo "  make test      - Run the unit tests using Rye"
	@echo "  make clean     - Clean up temporary files and caches"

install:
	@echo "Setting up project with Rye and installing dependencies..."
	@command -v rye >/dev/null 2>&1 || { echo >&2 "Rye is not installed. Please install it first: https://rye-up.com/guide/installation/"; exit 1; }
	@rye sync
	@echo "Project setup complete."
	@echo "To activate the environment, you can now run 'make source' or 'source .venv/bin/activate'."

source:
	@if [ -f ".venv/bin/activate" ]; then \
		echo "Spawning a new shell with the virtual environment activated."; \
		echo "Type 'exit' to return to your original shell."; \
		$(SHELL) -c "source .venv/bin/activate && exec $(SHELL)"; \
	else \
		echo "Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

lint:
	@echo "Running linter with Rye..."
	@rye run flake8 src

test:
	@echo "Running tests with Rye..."
	@rye run pytest

clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache build dist *.egg-info .venv .rye requirements*.lock
	@echo "Cleanup complete."
