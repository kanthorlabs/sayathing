# SayAThing Worker Queue Tests

This project now uses pytest for comprehensive testing of the worker queue system.

## Test Structure

- `worker/test_comprehensive.py` - Comprehensive test suite covering all queue functionality
- `worker/test_persistence.py` - Tests for database persistence across queue restarts

## Running Tests

### Quick Start
```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run with coverage report
make test-coverage
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

# Run tests during development
make test

# Check code quality
make check  # Runs lint + tests

# Clean up temporary files
make clean
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
