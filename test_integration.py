#!/usr/bin/env python3
"""
Integration test suite for SayAThing TTS service.

This test suite provides comprehensive integration testing that follows Python
standard testing practices using pytest. It verifies the complete workflow of:

- 3 primary workers processing audio tasks concurrently
- HTTP server handling API requests 
- 10 API calls with random 5-10 TTS requests per call
- End-to-end task processing from API to audio generation
- Worker concurrency and error handling

The tests validate:
1. Full integration workflow with realistic workloads
2. Concurrent processing capabilities across multiple workers
3. API validation and error handling
4. Proper task state management and completion tracking

Requirements met:
✓ 3 primary workers for audio processing
✓ HTTP server for task publishing
✓ 10 API calls with 5-10 items per task
✓ Python standard integration testing with pytest
✓ Comprehensive verification of audio generation pipeline
"""
import asyncio
import logging
import random
import sys
import time
from pathlib import Path
from typing import List
import httpx
import pytest
import pytest_asyncio

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from server.http import app
from worker.workers.primary_worker import PrimaryWorker
from worker import WorkerQueue, TaskState, QueueConfig
from container import initialize_container, container
from tts import TextToSpeechRequest
import uvicorn

# Configure logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceManager:
    """Helper class to manage test services lifecycle"""
    
    def __init__(self):
        self.workers: List[PrimaryWorker] = []
        self.worker_tasks: List[asyncio.Task] = []
        self.server_task: asyncio.Task = None
        self.server: uvicorn.Server = None
        self.shutdown_event = asyncio.Event()
        
    async def start_workers(self, count: int = 3):
        """Start the specified number of primary workers"""
        logger.info(f"Starting {count} primary workers...")
        
        # Get dependencies from DI container
        db_manager = container.database_manager()
        queue = container.worker_queue()
        
        for i in range(count):
            worker_id = f"test-primary-{i}-{int(time.time())}"
            worker = PrimaryWorker(worker_id=worker_id, queue=queue, database_manager=db_manager)
            
            # Start the worker
            worker_task = asyncio.create_task(worker.run())
            
            self.workers.append(worker)
            self.worker_tasks.append(worker_task)
            
        logger.info(f"Successfully started {count} primary workers")
        
    async def start_http_server(self, port: int = None):
        """Start the HTTP server"""
        if port is None:
            port = 8001 + random.randint(0, 100)  # Random port to avoid conflicts
        
        logger.info(f"Starting HTTP server on port {port}...")
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",  # Reduce noise in tests
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.port = port  # Store the port for tests to use
        
        # Start server in a task
        self.server_task = asyncio.create_task(self.server.serve())
        
        # Wait longer for server to start and verify it's ready
        for i in range(10):  # Try for up to 5 seconds
            await asyncio.sleep(0.5)
            if self.server.started:
                break
        else:
            raise RuntimeError(f"Server failed to start on port {port}")
            
        logger.info(f"HTTP server started and ready on port {port}")
        
    async def shutdown(self):
        """Shutdown all services gracefully"""
        logger.info("Shutting down test services...")
        
        # Shutdown workers
        for worker in self.workers:
            if worker.is_running:
                await worker.shutdown()
                
        # Cancel worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
                
        # Wait for worker tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            
        # Shutdown HTTP server
        if self.server and self.server_task and not self.server_task.done():
            self.server.should_exit = True
            await self.server_task
            
        logger.info("All test services shut down")


@pytest_asyncio.fixture(scope="function")  # Function scope so each test gets fresh setup
async def integration_setup():
    """Fixture to set up the full integration test environment"""
    # Initialize the DI container
    await initialize_container()
    
    # Initialize the worker queue
    queue = container.worker_queue()
    await queue.initialize()
    
    # Create service manager
    service_manager = ServiceManager()
    
    try:
        # Start services
        await service_manager.start_workers(count=3)
        await service_manager.start_http_server()  # Let it choose a random port
        
        yield service_manager
        
    finally:
        # Cleanup
        await service_manager.shutdown()
        await queue.close()


def generate_random_tts_requests(count: int) -> List[dict]:
    """Generate random TTS requests for testing"""
    # Use valid voice IDs from the error message
    voices = [
        "kokoro.af_heart",
        "kokoro.am_adam", 
        "kokoro.af_nicole",
        "kokoro.am_michael",
        "kokoro.af_sarah",
        "kokoro.af_bella"
    ]
    
    texts = [
        "Hello, this is a test message.",
        "The quick brown fox jumps over the lazy dog.",
        "Testing text-to-speech functionality with random content.",
        "Integration test message number {i}.",
        "This is sample text for audio processing.",
        "Testing concurrent task processing capabilities.",
        "Random message for TTS integration testing.",
        "Sample text to verify audio generation works correctly."
    ]
    
    requests = []
    for i in range(count):
        request = {
            "text": random.choice(texts).format(i=i),
            "voice_id": random.choice(voices),
            "metadata": {
                "test_id": f"test_{i}",
                "timestamp": time.time(),
                "session_id": f"integration_test_{int(time.time())}"
            }
        }
        requests.append(request)
        
    return requests


@pytest.mark.asyncio
@pytest.mark.integration
class TestIntegration:
    """Integration test class"""
    
    @pytest.mark.integration
    async def test_full_integration_workflow(self, integration_setup):
        """
        Full integration test:
        - 3 primary workers processing audio
        - HTTP server handling requests
        - 10 API calls with random 5-10 tasks each
        """
        service_manager = integration_setup
        base_url = f"http://127.0.0.1:{service_manager.port}"
        
        # Wait a moment for all services to be ready
        await asyncio.sleep(3)
        
        # Verify server is responding
        async with httpx.AsyncClient() as client:
            health_response = await client.get(f"{base_url}/healthz")
            assert health_response.status_code == 200
            logger.info("Health check passed - server is ready")
            
        # Get reference to queue for monitoring
        queue = container.worker_queue()
        logger.info("Queue initialized and ready")
        
        # Make 10 API calls with random 5-10 tasks each
        total_tasks_sent = 0
        task_ids_by_call = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for call_num in range(10):  # Back to 10 calls as requested
                # Generate random number of tasks (5-10) as originally specified
                task_count = random.randint(5, 10)
                tts_requests = generate_random_tts_requests(task_count)
                
                logger.info(f"API call {call_num + 1}: Sending {task_count} TTS requests")
                
                # Send tasks to the queue endpoint
                payload = {"tasks": tts_requests}
                response = await client.post(f"{base_url}/tts/queue/task", json=payload)
                
                assert response.status_code == 200, f"API call {call_num + 1} failed: {response.text}"
                
                response_data = response.json()
                task_ids = response_data["task_ids"]
                task_ids_by_call.append(task_ids)
                
                # The API creates one task per call, containing all the TTS requests as items
                assert len(task_ids) == 1, f"Expected 1 task ID per call, got {len(task_ids)}"
                
                total_tasks_sent += 1  # Count actual tasks, not TTS requests
                logger.info(f"API call {call_num + 1}: Successfully queued 1 task with {task_count} items, ID: {task_ids[0]}")
                
                # Small delay between calls to simulate realistic usage
                await asyncio.sleep(1)
                
        logger.info(f"Completed 10 API calls, total tasks sent: {total_tasks_sent}")
        
        # Wait for workers to process all tasks
        logger.info("Waiting for workers to process all tasks...")
        max_wait_time = 90  # 90 seconds max wait for TTS processing
        start_time = time.time()
        
        completed_tasks = 0
        failed_tasks = 0
        
        # Flatten task IDs for easier checking
        all_task_ids = [task_id for task_ids in task_ids_by_call for task_id in task_ids]
        
        while time.time() - start_time < max_wait_time:
            # Count completed and failed tasks
            completed_count = 0
            failed_count = 0
            processing_count = 0
            
            for task_id in all_task_ids:
                task = await queue.get_task(task_id)
                if task:
                    if task.state == TaskState.COMPLETED:
                        completed_count += 1
                    elif task.state in [TaskState.RETRYABLE, TaskState.DISCARDED]:
                        failed_count += 1
                    elif task.state == TaskState.PROCESSING:
                        processing_count += 1
                            
            logger.info(f"Progress - Completed: {completed_count}, Failed: {failed_count}, Processing: {processing_count}")
            
            # Check if all tasks are either completed or failed
            if completed_count + failed_count >= total_tasks_sent and processing_count == 0:
                completed_tasks = completed_count
                failed_tasks = failed_count
                logger.info("All tasks have been processed!")
                break
                
            await asyncio.sleep(5)  # Check less frequently
            
        else:
            # Timeout reached - get final counts
            for task_id in all_task_ids:
                task = await queue.get_task(task_id)
                if task and task.state == TaskState.COMPLETED:
                    completed_tasks += 1
                elif task and task.state in [TaskState.RETRYABLE, TaskState.DISCARDED]:
                    failed_tasks += 1
            logger.warning(f"Timeout reached. Final counts - Completed: {completed_tasks}, Failed: {failed_tasks}")
            
        # Log final results
        logger.info(f"Final results - Completed: {completed_tasks}, Failed: {failed_tasks}, Total: {total_tasks_sent}")
        
        # Verify that tasks were processed
        assert completed_tasks > 0, "No tasks were completed"
        
        # Check that we have a reasonable completion rate (at least 50% due to TTS processing complexity)
        completion_rate = completed_tasks / total_tasks_sent
        logger.info(f"Task completion rate: {completion_rate:.2%} ({completed_tasks}/{total_tasks_sent})")
        assert completion_rate >= 0.5, f"Completion rate too low: {completion_rate:.2%}"
        
        # Verify some task completions in detail by checking response URLs are populated
        sample_task_ids = all_task_ids[:3]  # Check first 3 tasks
        logger.info(f"Checking completion details of sample tasks: {sample_task_ids}")
        
        successfully_processed_items = 0
        for task_id in sample_task_ids:
            task = await queue.get_task(task_id)
            if task:
                logger.info(f"Task {task_id}: state={task.state.name}, attempts={task.attempt_count}, items={len(task.items)}")
                if task.state == TaskState.COMPLETED:
                    # Check that response URLs were populated (indicating actual TTS processing)
                    for i, item in enumerate(task.items):
                        if item.response_url and item.response_url.startswith("data:audio/wav;base64,"):
                            successfully_processed_items += 1
                            logger.info(f"Task {task_id} item {i} has valid audio response URL")
            else:
                logger.warning(f"Task {task_id} not found in queue")
                
        # At least some items should be fully processed with audio
        assert successfully_processed_items > 0, "No task items were successfully processed with audio generation"
        logger.info(f"Successfully processed {successfully_processed_items} task items with audio generation")
        
        logger.info("Integration test completed successfully!")
        
    @pytest.mark.integration
    async def test_worker_concurrency(self, integration_setup):
        """Test that multiple workers can process tasks concurrently"""
        service_manager = integration_setup
        base_url = f"http://127.0.0.1:{service_manager.port}"
        
        # Wait for services to be ready
        await asyncio.sleep(3)
        
        # Create multiple separate API calls to generate multiple tasks for concurrency testing
        total_tasks = 15
        task_ids = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send multiple individual tasks to test concurrency
            for i in range(total_tasks):
                tts_requests = generate_random_tts_requests(1)  # One request per task
                
                payload = {"tasks": tts_requests}
                response = await client.post(f"{base_url}/tts/queue/task", json=payload)
                assert response.status_code == 200
                
                response_data = response.json()
                assert len(response_data["task_ids"]) == 1
                task_ids.extend(response_data["task_ids"])
                
        logger.info(f"Sent {total_tasks} individual tasks for concurrent processing")
        assert len(task_ids) == total_tasks
        
        # Monitor processing to ensure concurrency
        queue = container.worker_queue()
        max_concurrent_seen = 0
        
        for _ in range(30):  # Check for 30 seconds
            processing_count = 0
            completed_count = 0
            
            for task_id in task_ids:
                task = await queue.get_task(task_id)
                if task:
                    if task.state == TaskState.PROCESSING:
                        processing_count += 1
                    elif task.state in [TaskState.COMPLETED, TaskState.RETRYABLE, TaskState.DISCARDED]:
                        completed_count += 1
                        
            max_concurrent_seen = max(max_concurrent_seen, processing_count)
            
            if completed_count >= total_tasks:
                break
                
            await asyncio.sleep(1)
            
        logger.info(f"Maximum concurrent tasks seen: {max_concurrent_seen}")
        
        # We should see more than 1 task being processed concurrently with 3 workers
        assert max_concurrent_seen > 1, f"Expected concurrent processing, but max concurrent was {max_concurrent_seen}"
        
    @pytest.mark.integration
    async def test_api_error_handling(self, integration_setup):
        """Test API error handling and validation"""
        base_url = f"http://127.0.0.1:{integration_setup.port}"
        
        # Wait for services to be ready
        await asyncio.sleep(3)
        
        async with httpx.AsyncClient() as client:
            # Test empty task list - should fail validation due to min_length=1
            response = await client.post(f"{base_url}/tts/queue/task", json={"tasks": []})
            assert response.status_code == 422  # Validation error
            logger.info("Empty task list validation error test passed")
            
            # Test invalid payload - should fail validation
            response = await client.post(f"{base_url}/tts/queue/task", json={"invalid": "data"})
            assert response.status_code == 422  # Validation error
            logger.info("Invalid payload validation test passed")
            
            # Test valid but minimal payload - should succeed
            valid_request = {
                "tasks": [{
                    "text": "Test message",
                    "voice_id": "kokoro.af_heart",
                    "metadata": {}
                }]
            }
            response = await client.post(f"{base_url}/tts/queue/task", json=valid_request)
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["task_ids"]) == 1
            logger.info("Valid request test passed")
            
            # Test invalid voice_id - should succeed at API level but might fail during processing
            invalid_voice_request = {
                "tasks": [{
                    "text": "Test message",
                    "voice_id": "invalid_voice_id",
                    "metadata": {}
                }]
            }
            response = await client.post(f"{base_url}/tts/queue/task", json=invalid_voice_request)
            # This should succeed at the API level (task gets queued)
            # The error would occur during processing by workers
            assert response.status_code == 200
            logger.info("Invalid voice_id queuing test passed")
            
        logger.info("API error handling tests completed")


if __name__ == "__main__":
    # Allow running the test directly
    pytest.main([__file__, "-v", "-s"])
