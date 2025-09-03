# Makefile for SayAThing Worker Queue Tests
.PHONY: help test test-verbose test-comprehensive test-persistence test-coverage clean install install-dev lint format check

# Default target
help:
	@echo "Available targets:"
	@echo "  test              - Run all tests"
	@echo "  test-verbose      - Run all tests with verbose output"
	@echo "  test-comprehensive - Run comprehensive tests only"
	@echo "  test-persistence  - Run persistence tests only"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  install           - Install production dependencies"
	@echo "  install-dev       - Install development dependencies"
	@echo "  lint              - Run linting checks"
	@echo "  format            - Format code"
	@echo "  check             - Run all checks (lint + tests)"
	@echo "  clean             - Clean up temporary files"

# Test targets
test:
	@echo "Running all worker queue tests..."
	python -m pytest worker/ -v

test-verbose:
	@echo "Running all worker queue tests with verbose output..."
	python -m pytest worker/ -vvv --tb=long

test-comprehensive:
	@echo "Running comprehensive worker queue tests..."
	python -m pytest worker/test_comprehensive.py -v

test-persistence:
	@echo "Running persistence tests..."
	python -m pytest worker/test_persistence.py -v

test-coverage:
	@echo "Running tests with coverage report..."
	python -m pytest worker/ --cov=worker --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/"

# Test specific patterns
test-pattern:
	@echo "Running tests matching pattern: $(PATTERN)"
	python -m pytest worker/ -k "$(PATTERN)" -v

# Development dependencies
install:
	@echo "Installing production dependencies..."
	uv sync --no-dev

install-dev:
	@echo "Installing development dependencies..."
	uv sync
	uv add --dev pytest pytest-asyncio pytest-cov

# Code quality
lint:
	@echo "Running linting checks..."
	python -m flake8 worker/ --max-line-length=120 --ignore=E203,W503
	python -m mypy worker/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	python -m black worker/ --line-length=120
	python -m isort worker/

check: lint test
	@echo "All checks passed!"

# Cleanup
clean:
	@echo "Cleaning up temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -name "*.db" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

# Quick test targets for specific scenarios
test-enqueue:
	python -m pytest worker/test_comprehensive.py::test_enqueue_dequeue -v

test-retry:
	python -m pytest worker/test_comprehensive.py::test_retry_mechanism -v

test-states:
	python -m pytest worker/test_comprehensive.py::test_state_transitions -v

# Run tests in parallel (if pytest-xdist is installed)
test-parallel:
	@echo "Running tests in parallel..."
	python -m pytest worker/ -n auto -v

# Watch mode (if pytest-watch is installed)
test-watch:
	@echo "Running tests in watch mode..."
	cd worker && ptw -- -v

# Generate test report
test-report:
	@echo "Generating test report..."
	python -m pytest worker/ --html=report.html --self-contained-html -v
	@echo "Test report generated: report.html"
