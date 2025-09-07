#!/bin/bash
# Test runner script for SayAThing project
# 
# Usage:
#   ./run_tests.sh                    # Run all tests except integration tests
#   ./run_tests.sh --integration      # Run all tests including integration tests
#   ./run_tests.sh --integration-only # Run only integration tests
#   ./run_tests.sh --help            # Show this help

set -e

print_help() {
    echo "SayAThing Test Runner"
    echo ""
    echo "Usage:"
    echo "  $0                    Run all tests except integration tests (default)"
    echo "  $0 --integration      Run all tests including integration tests"
    echo "  $0 --integration-only Run only integration tests"
    echo "  $0 --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Fast test run for development"
    echo "  $0 --integration                      # Full test suite"
    echo "  $0 --integration-only                 # Only long-running integration tests"
    echo ""
}

run_default_tests() {
    echo "🔍 Running fast test suite (excluding integration tests)..."
    echo "⏱️  This should take ~15-30 seconds"
    echo ""
    python -m pytest -v
}

run_all_tests() {
    echo "🔍 Running full test suite (including integration tests)..."
    echo "⏱️  This may take 2-3 minutes due to TTS processing"
    echo ""
    python -m pytest --integration -v
}

run_integration_only() {
    echo "🔍 Running integration tests only..."
    echo "⏱️  This may take 1-2 minutes due to TTS processing"
    echo ""
    python -m pytest -m integration --integration -v
}

case "${1:-}" in
    --integration)
        run_all_tests
        ;;
    --integration-only)
        run_integration_only
        ;;
    --help|-h)
        print_help
        ;;
    "")
        run_default_tests
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo ""
        print_help
        exit 1
        ;;
esac

echo ""
echo "✅ Tests completed!"
