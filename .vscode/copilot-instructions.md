# GitHub Copilot Instructions for SayAThing

## Project Overview

**SayAThing** is an open-source Text-to-Speech (TTS) API platform powered by the Kokoro engine and FastAPI. The project provides a robust, scalable TTS service with a worker queue system for handling audio generation tasks.

### Key Features
- **TTS API**: RESTful API for text-to-speech conversion using Kokoro engine
- **Worker Queue System**: SQLite-backed queue with retry mechanisms for reliable processing
- **Dependency Injection**: Singleton pattern for shared resources using `python-dependency-injector`
- **Voice Management**: Support for multiple voices with preloading capabilities
- **Dashboard**: Web interface for monitoring and management

## Documentation Reference

**Important**: For detailed information about specific topics, always check the documentation in `./docs/` first:

- **`./docs/onboarding.md`**: Complete engineer onboarding guide with codebase overview, development setup, coding standards, and testing practices
- **`./docs/dependency_injection.md`**: Detailed explanation of the DI implementation, singleton patterns, and how to use the container system
- **`./docs/testing.md`**: Comprehensive testing guide including test structure, running tests, fixtures, and integration test configuration
- **`./docs/worker_queue.solution.md`**: In-depth worker queue implementation details, database schema, and operational patterns

When answering questions about:
- **Project setup, development environment, or coding standards** → Reference `./docs/onboarding.md`
- **Dependency injection, container usage, or singleton patterns** → Reference `./docs/dependency_injection.md`
- **Testing approaches, fixtures, or test execution** → Reference `./docs/testing.md`
- **Worker queue operations, database schema, or task management** → Reference `./docs/worker_queue.solution.md`

Always suggest that users consult the relevant documentation for comprehensive details beyond what's covered in this instructions file.

## Architecture & Structure

### Core Components

1. **Server Layer** (`server/`)
   - **FastAPI Application**: Main HTTP server with async request handling
   - **Routes**: Modular API endpoints (`/api/tts`, `/tts/voices`, `/healthz`, dashboard)
   - **Config**: Application configuration and dependency injection setup
   - **Exception Handlers**: Centralized error handling for TTS operations

2. **TTS Engine** (`tts/`)
   - **Engine Interface**: Abstract base for TTS implementations
   - **Kokoro Engine**: Primary TTS implementation with voice preloading
   - **Voice Management**: Voice metadata, loading, and sample generation
   - **Request/Response Models**: Pydantic models for API schemas

3. **Worker System** (`worker/`)
   - **Queue**: SQLite-backed persistent queue with atomic operations
   - **Database**: SQLAlchemy ORM with task state management
   - **Workers**: Primary and retry workers for task processing
   - **Task Management**: ULID-based task IDs with state transitions

4. **Dependency Injection** (`container.py`)
   - **Singleton DatabaseManager**: Shared database instance across all components
   - **Factory Pattern**: WorkerQueue instances with injected dependencies
   - **Test Containers**: Isolated DI containers for testing

### Dependencies & Tech Stack

- **Python 3.12+** (required)
- **FastAPI**: Async web framework with OpenAPI documentation
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Default database (with aiosqlite for async)
- **Kokoro**: TTS engine for voice synthesis
- **dependency-injector**: DI container management
- **pytest**: Testing framework with async support
- **uv**: Package manager (preferred) with lock file support

## Development Guidelines

### Code Style & Conventions

- **Type Hints**: Always use full type annotations for functions and variables
- **Async/Await**: Prefer async patterns for I/O operations
- **Naming Conventions**:
  - Files/modules: `snake_case.py`
  - Variables/functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Docstrings**: Use comprehensive docstrings for public APIs
- **Error Handling**: Use custom exception classes with descriptive messages

### File Organization Rules

- **Server Routes**: Keep endpoints in `server/routes/` with clear tagging
- **TTS Engines**: Implement `TTSEngineInterface` in `tts/` directory
- **Worker Logic**: Place worker implementations in `worker/workers/`
- **Configuration**: Use environment variables with defaults in config classes
- **Tests**: Co-locate tests with modules using `test_*.py` naming

### API Design Patterns

- **Request/Response Models**: Use Pydantic for validation and serialization
- **Error Responses**: Standardized HTTP status codes with descriptive messages
- **OpenAPI Documentation**: Include examples, descriptions, and response schemas
- **Async Handlers**: All route handlers should be async functions
- **Dependency Injection**: Use container for shared resources in routes

### Database & Queue Patterns

- **ULID Primary Keys**: Use `ulid-py` for sortable, unique task identifiers
- **Atomic Operations**: Use SQLAlchemy transactions for consistency
- **State Management**: Enforce valid task state transitions
- **Optimistic Concurrency**: Prevent race conditions with version checking
- **Bulk Operations**: Use batch operations for performance

### Worker System Guidelines

- **Pull-Based Model**: Workers actively request tasks from queue
- **Visibility Timeout**: Prevent duplicate processing with timeout mechanisms
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Error Logging**: Capture and store error details for debugging
- **Graceful Shutdown**: Handle signals properly for clean termination

## Testing Approach

### Test Structure
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: End-to-end tests marked with `@pytest.mark.integration`
- **Test Fixtures**: Reusable fixtures for database and queue setup
- **Test Containers**: Isolated DI containers for test environments

### Testing Commands
```bash
# Fast unit tests (exclude integration)
make test

# All tests including integration
make test-integration

# Coverage reporting
make test-coverage

# Integration tests only
make test-integration-only
```

### Test Data Management
- **In-Memory SQLite**: Use `:memory:` for fast test execution
- **Fixture Cleanup**: Automatic cleanup of test resources
- **Isolated Containers**: Separate DI containers for test isolation

## Environment Configuration

### Environment Variables
- `TTS_THREAD_POOL_MAX_WORKERS` (default: 4)
- `TTS_GENERATION_TIMEOUT` (default: 30.0 seconds)
- `VOICE_PRELOAD_TIMEOUT` (default: 120.0 seconds)
- `MAX_CONCURRENT_VOICE_SAMPLES` (default: 10)

### Development Setup
```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn server.http:app --reload --log-level debug

# Run with workers
python main.py --primary-workers 2 --retry-workers 1
```

## Common Patterns & Best Practices

### Error Handling
```python
# Use custom exceptions with descriptive messages
raise VoiceNotFoundError(voice_id, available_voices)

# Handle specific errors in routes
@router.post("/api/tts")
async def text_to_speech(request: TextToSpeechRequest):
    try:
        return await engine.generate_audio(request)
    except VoiceNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Dependency Injection Usage
```python
# Get dependencies from container
queue = container.worker_queue()
db_manager = container.database_manager()

# For testing, use isolated containers
test_container = create_test_container(test_config)
```

### Async Task Processing
```python
# Worker pattern for queue processing
async def process_tasks(self):
    while not self.shutdown_event.is_set():
        tasks = await self.queue.dequeue(size=self.batch_size)
        if tasks:
            await asyncio.gather(*[self.process_task(task) for task in tasks])
        await asyncio.sleep(self.poll_interval)
```

### Voice Engine Implementation
```python
# Implement TTSEngineInterface for new engines
class NewEngine(TTSEngineInterface):
    async def generate_audio_async(self, text: str, voice_id: str) -> bytes:
        # Implementation here
        pass
    
    async def preload_voice_async(self, voice_id: str) -> bool:
        # Voice preloading logic
        pass
```

## Security & Performance Considerations

- **Input Validation**: Use Pydantic models for request validation
- **Rate Limiting**: Consider implementing rate limiting for API endpoints
- **Resource Management**: Use thread pools for CPU-intensive TTS operations
- **Memory Usage**: Monitor memory usage during voice preloading
- **Database Connections**: Use connection pooling for database operations

## Debugging & Monitoring

### Logging
- Use structured logging with appropriate log levels
- Include request IDs for tracing across components
- Log performance metrics for TTS generation times

### Health Checks
- `/healthz` endpoint for service health monitoring
- Database connectivity checks
- Worker queue status monitoring

### Dashboard
- Web interface at `/dashboard` for system monitoring
- Real-time task queue status and metrics
- Worker performance and error tracking

## Integration Points

### Adding New TTS Engines
1. Implement `TTSEngineInterface`
2. Register in engine factory (`tts/tts.py`)
3. Add voice definitions to voice registry
4. Update API documentation

### Adding New API Endpoints
1. Create route handler in `server/routes/`
2. Define Pydantic models for request/response
3. Add exception handling
4. Include router in `server/http.py`
5. Update OpenAPI documentation

### Worker Extensions
1. Extend task types in `worker/task.py`
2. Implement processing logic in workers
3. Add state transition handling
4. Include in dependency injection container

This project emphasizes reliability, performance, and maintainability. Always consider error handling, testing, and documentation when making changes.
