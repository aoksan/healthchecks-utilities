# Makefile for healthchecks-utilities

.PHONY: help lint test clean install

help:
	@echo "Available commands:"
	@echo "  make install   - Create a virtual environment and install dependencies"
	@echo "  make lint      - Run the linter on the source code"
	@echo "  make test      - Run the unit tests"
	@echo "  make clean     - Clean up temporary files and caches"

install:
	@echo "Creating virtual environment in ./venv and installing dependencies..."
	python3 -m venv venv
	@. venv/bin/activate; pip install --upgrade pip
	@. venv/bin/activate; pip install -r requirements.txt -e .
	@echo "Virtual environment created. Run 'source venv/bin/activate' to use it."

lint:
	@echo "Running linter..."
	@. venv/bin/activate; flake8 src

test:
	@echo "Running tests..."
	@. venv/bin/activate; pytest

clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache build dist *.egg-info
	@echo "Cleanup complete."
