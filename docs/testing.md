# SayAThing Worker Queue Tests

This project now uses pytest for comprehensive testing of the worker queue system.

## Test Structure

- `worker/test_comprehensive.py` - Comprehensive test suite covering all queue functionality
- `worker/test_persistence.py` - Tests for database persistence across queue restarts
- `test_integration.py` - Full integration tests (marked with `@pytest.mark.integration`)
- `test_di.py` - Dependency injection container tests
- `test_shared_db.py` - Shared database functionality tests

## Running Tests

### Quick Start
```bash
# Run all tests (excluding long-running integration tests)
make test

# Run all tests including integration tests
make test-integration

# Run only integration tests
make test-integration-only

# Run with verbose output
make test-verbose

# Run with coverage report (excluding integration tests)
make test-coverage

# Run with coverage report including integration tests
make test-coverage-all
```

### Integration Tests
```bash
# Run only integration tests
make test-integration-only

# Run all tests including integration tests
make test-integration
# or alternatively:
make test-all

# Skip integration tests explicitly (default behavior)
make test
```

### Individual Test Suites
```bash
# Run comprehensive tests only
make test-comprehensive

# Run persistence tests only
make test-persistence
```

### Specific Test Cases
```bash
# Test enqueue/dequeue functionality
make test-enqueue

# Test retry mechanism
make test-retry

# Test state transitions
make test-states
```

### Coverage and Reports
```bash
# Generate coverage report (creates htmlcov/ directory)
make test-coverage

# Generate HTML test report
make test-report
```

### Advanced Testing
```bash
# Run tests matching a pattern
make test-pattern PATTERN="retry"

# Run tests in parallel (requires pytest-xdist)
make test-parallel
```

## Test Features

### Comprehensive Test Suite (`test_comprehensive.py`)
- **Enqueue/Dequeue**: Basic queue operations
- **State Transitions**: Task lifecycle management
- **Retry Mechanism**: Exponential backoff and retry logic
- **Visibility Timeout**: Handling of stale processing tasks
- **Max Attempts**: Auto-discard after maximum retry attempts
- **Cancel/Resume**: Task cancellation and resumption
- **Error Handling**: Comprehensive error case coverage

### Persistence Test Suite (`test_persistence.py`)
- **Database Persistence**: Verifies tasks persist across queue restarts
- **Temporary Directories**: Uses system temp directories for isolation
- **Cross-Session Validation**: Ensures data integrity between sessions

## Test Configuration

### Fixtures
- `queue_config`: Provides in-memory SQLite configuration for fast testing
- `worker_queue`: Initialized queue instance with automatic cleanup

### Dependencies
- `pytest`: Main testing framework
- `pytest-asyncio`: Async test support
- `pytest-cov`: Coverage reporting

## Development Workflow

```bash
# Setup development environment
make install-dev

# Run tests during development (excludes integration tests)
make test

# Run all tests including integration tests
make test-integration

# Check code quality
make check  # Runs lint + tests

# Clean up temporary files
make clean
```

## Integration Test Configuration

### Test Markers
The project uses pytest markers to categorize tests:
- `@pytest.mark.integration`: Marks long-running integration tests
- Integration tests are **skipped by default** to speed up development workflow
- Use `--integration` flag to include integration tests in the test run

### Custom Pytest Flags
- `--integration`: Enables integration tests (disabled by default)
- Integration tests can take 60+ seconds to complete due to TTS processing

### Integration Test Features
- **Full End-to-End Testing**: Complete workflow from API to audio generation
- **Multi-Worker Concurrency**: Tests 3 primary workers processing tasks simultaneously
- **HTTP Server Integration**: Real API endpoints with request/response validation
- **Realistic Workloads**: 10 API calls with 5-10 TTS requests each
- **Error Handling**: Comprehensive API validation and worker error scenarios

### Configuration Files
- `conftest.py`: Custom pytest configuration and command-line options
- `pyproject.toml`: Pytest settings including marker definitions
- Integration tests marked with `@pytest.mark.integration` decorator

### Running Integration Tests
```bash
# Run all tests including integration (full test suite)
make test-integration

# Run only integration tests
make test-integration-only

# Run specific integration test
pytest test_integration.py::TestIntegration::test_full_integration_workflow --integration

# Default behavior (skip integration tests)
make test
```

## Performance Notes

The tests have been optimized for performance:
- Removed `get_queue_stats()` method that caused expensive table scans
- Use in-memory databases for fast test execution
- Temporary directories for isolation without cleanup overhead
- Async fixtures for proper resource management

## Coverage

Current test coverage is ~94% with the following areas covered:
- Queue operations (enqueue, dequeue, retry)
- State management and transitions
- Error handling and edge cases
- Database persistence
- Configuration management
