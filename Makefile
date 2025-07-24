# Makefile for healthchecks-utilities

# Default command to run if none is specified, e.g., make run
CMD ?= check

.PHONY: all lint test run clean

all: lint test

lint:
	@echo "Running linter..."
	@flake8 .

test:
	@echo "Running tests..."
	@pytest

run:
	@echo "Running the application with command: $(CMD)..."
	@python3 main.py $(CMD)

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache
