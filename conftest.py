#!/usr/bin/env python3
"""
pytest configuration and custom options.

This module provides custom pytest configuration including:
- Custom command line options for test selection
- Integration test handling with --integration flag
"""
import pytest


def pytest_addoption(parser):
    """Add custom command line options to pytest."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (long-running tests)"
    )


def pytest_configure(config):
    """Configure pytest with custom markers and behaviors."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    if config.getoption("--integration"):
        # If --integration flag is provided, run all tests including integration tests
        return
    
    # Skip integration tests by default
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
