# Integration Tests

This directory contains comprehensive integration tests for the SayAThing TTS service.

## Test Overview

The integration test suite (`test_integration.py`) provides end-to-end testing that validates:

- **3 primary workers** processing audio tasks concurrently
- **HTTP server** handling API requests
- **10 API calls** with random 5-10 TTS requests per call
- **Complete audio generation pipeline** from API to base64-encoded audio output
- **Worker concurrency** and proper task distribution
- **Error handling** and API validation

## Requirements Met

✅ 3 primary workers for audio processing  
✅ HTTP server for task publishing via API  
✅ 10 API calls with 5-10 items per task  
✅ Python standard integration testing practices with pytest  
✅ Comprehensive verification of the complete workflow  

## Running the Tests

### Run all integration tests:
```bash
python -m pytest test_integration.py -v
```

### Run specific test:
```bash
# Full integration workflow test
python -m pytest test_integration.py::TestIntegration::test_full_integration_workflow -v

# Worker concurrency test
python -m pytest test_integration.py::TestIntegration::test_worker_concurrency -v

# API error handling test
python -m pytest test_integration.py::TestIntegration::test_api_error_handling -v
```

### Run with detailed output:
```bash
python -m pytest test_integration.py -v -s
```

## Test Details

### 1. Full Integration Workflow Test
- Starts 3 primary workers and HTTP server
- Makes 10 API calls with 5-10 TTS requests each
- Monitors task completion and verifies audio generation
- Validates at least 50% completion rate
- Checks that response URLs contain valid base64 audio data

### 2. Worker Concurrency Test
- Sends 15 individual tasks to test concurrent processing
- Monitors task states to verify multiple workers process simultaneously
- Ensures more than 1 task is processed concurrently

### 3. API Error Handling Test
- Tests empty task list validation (expects 422 error)
- Tests invalid payload validation (expects 422 error)
- Tests valid requests (expects 200 success)
- Tests invalid voice IDs (queues successfully, fails during processing)

## Dependencies

The tests require these additional dependencies (automatically installed):
- `httpx` - For making HTTP requests to the API
- `orjson` - Required by FastAPI's ORJSONResponse

## Test Architecture

The test suite uses a `ServiceManager` class to:
- Initialize dependency injection container
- Start and manage worker processes
- Start and manage HTTP server on random ports
- Handle graceful shutdown of all services

Each test gets a fresh set of services to avoid interference between tests.

## Expected Duration

- Full integration test: ~1-2 minutes (depends on TTS processing time)
- Worker concurrency test: ~30-45 seconds
- API error handling test: ~10-15 seconds
- Complete test suite: ~2-4 minutes

The tests are designed to be realistic and may take time due to actual TTS audio generation.
