# Makefile for healthchecks-utilities

# --- Standard Utility Commands ---

.PHONY: help lint test clean install

# List of commands this Makefile knows about, to prevent them from being passed to the script.
KNOWN_TARGETS := help lint test clean install

help:
	@echo "Usage: make <command> [arguments]"
	@echo ""
	@echo "Utility Commands:"
	@echo "  install        Install dependencies from requirements.txt into a venv"
	@echo "  lint           Run the flake8 linter"
	@echo "  test           Run pytest"
	@echo "  clean          Remove temporary Python files"
	@echo ""
	@echo "Application Commands (passed to main.py):"
	@echo "  check          Check status/expiry for all domains"
	@echo "  list-checks    List all checks from the API"
	@echo "  create [...]   Create new healthchecks"
	@echo "  remove [...]   Remove healthchecks"
	@echo "  ... and any other command supported by main.py"

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

# --- Catch-all for Application Commands ---
# This is the magic part. The '%' is a wildcard that matches any target
# that hasn't been explicitly defined above.
# It forwards the entire command and its arguments to main.py.
%:
	@# Filter out known make targets from the command goals
	$(eval CMD_ARGS := $(filter-out $(KNOWN_TARGETS), $(MAKECMDGOALS)))
	@if [ -z "$(CMD_ARGS)" ]; then \
		echo "Error: No command specified for main.py."; \
		make help; \
		exit 1; \
	fi
	@echo "Running: python3 main.py $(CMD_ARGS)"
	@python3 main.py $(CMD_ARGS)
