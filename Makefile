# Makefile for SayAThing Worker Queue Tests
.PHONY: help test test-verbose test-comprehensive test-persistence test-coverage test-coverage-all test-integration test-integration-only test-all clean install install-dev lint lint-strict type-check format check

# Default target
help:
	@echo "Available targets:"
	@echo "  test              - Run all tests (excluding integration tests)"
	@echo "  test-all          - Run all tests including integration tests"
	@echo "  test-integration  - Run all tests including integration tests"
	@echo "  test-integration-only - Run only integration tests"
	@echo "  test-verbose      - Run all tests with verbose output"
	@echo "  test-coverage     - Run tests with coverage report (excluding integration)"
	@echo "  test-coverage-all - Run all tests with coverage report (including integration)"
	@echo "  install           - Install production dependencies"
	@echo "  install-dev       - Install development dependencies"
	@echo "  lint              - Run linting checks (code style only)"
	@echo "  lint-strict       - Run strict linting checks (including type checking)"
	@echo "  type-check        - Run type checking only"
	@echo "  format            - Format code"
	@echo "  check             - Run all checks (lint + tests)"
	@echo "  clean             - Clean up temporary files"

# Test targets
test:
	@echo "Running all tests (excluding integration tests)..."
	@echo "⏱️  This should take ~15-30 seconds"
	python -m pytest -v

test-all: test-integration

test-integration:
	@echo "Running all tests including integration tests..."
	@echo "⚠️  Integration tests may take 2-3 minutes due to TTS processing"
	python -m pytest --integration -v

test-integration-only:
	@echo "Running integration tests only..."
	@echo "⚠️  This may take 1-2 minutes due to TTS processing"
	python -m pytest -m integration --integration -v

test-verbose:
	@echo "Running all tests with verbose output (excluding integration tests)..."
	python -m pytest -vvv --tb=long

test-coverage:
	@echo "Running tests with coverage report (excluding integration tests)..."
	python -m pytest --cov=worker --cov=server --cov=tts --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/"

test-coverage-all:
	@echo "Running all tests with coverage report (including integration tests)..."
	@echo "⚠️  This may take 2-3 minutes due to integration tests"
	python -m pytest --integration --cov=worker --cov=server --cov=tts --cov-report=html --cov-report=term-missing -v
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
	uv add --dev pytest pytest-asyncio pytest-cov black flake8 mypy isort

# Code quality
lint:
	@echo "Running linting checks..."
	python -m flake8 server/ tts/ worker/ *.py --max-line-length=140 --ignore=W293,E402
	@echo "✅ Linting checks passed!"

lint-strict:
	@echo "Running strict linting checks (including type checking)..."
	python -m flake8 server/ tts/ worker/ *.py --max-line-length=140 --ignore=W293,E402
	python -m mypy server/ tts/ worker/ --ignore-missing-imports --explicit-package-bases
	@echo "✅ Strict linting checks passed!"

format:
	@echo "Formatting code..."
	python -m black server/ tts/ worker/ *.py --line-length=120
	python -m isort server/ tts/ worker/ *.py

check: format lint test
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
