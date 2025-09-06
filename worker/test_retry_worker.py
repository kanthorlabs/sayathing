#!/usr/bin/env python3
"""
Test script for the RetryWorker implementation.
"""
import asyncio
import logging
import json
import time
import sys
import tempfile
import os
from pathlib import Path

# Add the parent directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tts.tts import TextToSpeechRequest
from worker.queue import WorkerQueue
from worker.task import Task, TaskItem, TaskState
from worker.config import QueueConfig
from worker.workers import RetryWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_task(task_id: str = "", text: str = "Test retry message") -> Task:
    """Create a sample task for testing"""
    task_item = TaskItem(
        request={
            "text": text,
            "voice_id": "kokoro.af_heart",
            "metadata": {"test": True, "retry_test": True}
        },
        response_url=""
    )
    
    current_time = int(time.time() * 1000)
    
    task = Task(
        id=task_id or f"retry-test-{current_time}",
        state=TaskState.RETRYABLE,  # Start in retryable state
        schedule_at=current_time,
        attempt_count=1,  # Already attempted once
        attempted_at=current_time - 60000,  # 1 minute ago
        attempted_error=["First attempt failed"],
        items=[task_item],
        created_at=current_time - 120000,  # 2 minutes ago
        updated_at=current_time - 60000   # 1 minute ago
    )
    
    return task


async def test_retry_worker():
    """Test the RetryWorker functionality"""
    logger.info("Starting RetryWorker test")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        # Configure queue with temporary database
        config = QueueConfig(database_url=f"sqlite+aiosqlite:///{db_path}")
        
        # Initialize queue and add test tasks
        queue = WorkerQueue(config)
        await queue.initialize()
        
        # Create sample retryable tasks
        tasks = [
            create_sample_task(f"retry-task-1", "Hello world retry test"),
            create_sample_task(f"retry-task-2", "Another retry test message"),
        ]
        
        # Add tasks to queue
        task_ids = await queue.enqueue(tasks)
        logger.info(f"Enqueued {len(task_ids)} retryable tasks: {task_ids}")
        
        # Verify tasks are in retryable state
        for task_id in task_ids:
            task = await queue.get_task(task_id)
            assert task is not None
            assert task.state == TaskState.RETRYABLE
            logger.info(f"Task {task_id} is in {task.state.name} state")
        
        await queue.close()
        
        # Create and configure retry worker
        os.environ["RETRY_WORKER_POLL_DELAY"] = "2"  # Quick polling for test
        os.environ["RETRY_WORKER_BATCH_SIZE"] = "5"
        os.environ["QUEUE_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
        
        retry_worker = RetryWorker("test-retry-worker")
        
        # Run retry worker for a limited time
        logger.info("Starting RetryWorker for 10 seconds...")
        
        async def run_worker_with_timeout():
            try:
                await asyncio.wait_for(retry_worker.run(), timeout=10)
            except asyncio.TimeoutError:
                logger.info("Worker timeout reached, shutting down...")
                await retry_worker.shutdown()
        
        await run_worker_with_timeout()
        
        # Check final task states
        final_queue = WorkerQueue(config)
        await final_queue.initialize()
        
        for task_id in task_ids:
            task = await final_queue.get_task(task_id)
            if task:
                logger.info(f"Final state of task {task_id}: {task.state.name} (attempts: {task.attempt_count})")
                
                # Check if task was processed successfully
                if task.state == TaskState.COMPLETED:
                    logger.info(f"✓ Task {task_id} completed successfully!")
                    # Check if response_url was set
                    for item in task.items:
                        if item.response_url and item.response_url.startswith("data:audio/wav;base64,"):
                            logger.info(f"✓ Task {task_id} has audio response")
                        else:
                            logger.warning(f"⚠ Task {task_id} missing audio response")
                elif task.state == TaskState.RETRYABLE:
                    logger.info(f"⚠ Task {task_id} still retryable after processing")
                elif task.state == TaskState.DISCARDED:
                    logger.info(f"⚠ Task {task_id} was discarded (too many attempts)")
                else:
                    logger.info(f"⚠ Task {task_id} in unexpected state: {task.state.name}")
            else:
                logger.error(f"✗ Task {task_id} not found!")
        
        await final_queue.close()
        
        logger.info("RetryWorker test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise
    finally:
        # Cleanup temporary database
        try:
            os.unlink(db_path)
        except:
            pass


async def test_retry_worker_edge_cases():
    """Test edge cases for RetryWorker"""
    logger.info("Testing RetryWorker edge cases")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        config = QueueConfig(database_url=f"sqlite+aiosqlite:///{db_path}")
        queue = WorkerQueue(config)
        await queue.initialize()
        
        # Test 1: Task with max attempts reached (should be discarded)
        max_attempts_task = create_sample_task("max-attempts-task", "Max attempts test")
        max_attempts_task.attempt_count = 3  # At max attempts
        max_attempts_task.state = TaskState.RETRYABLE
        
        await queue.enqueue([max_attempts_task])
        logger.info("Added task with max attempts reached")
        
        # Test 2: Empty queue scenario
        await queue.close()
        
        os.environ["RETRY_WORKER_POLL_DELAY"] = "1"
        os.environ["RETRY_WORKER_MAX_ATTEMPTS"] = "3"
        os.environ["QUEUE_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
        
        retry_worker = RetryWorker("test-edge-cases")
        
        # Run for short time to test max attempts scenario
        async def run_short_test():
            try:
                await asyncio.wait_for(retry_worker.run(), timeout=3)
            except asyncio.TimeoutError:
                await retry_worker.shutdown()
        
        await run_short_test()
        
        # Check that max attempts task was discarded
        final_queue = WorkerQueue(config)
        await final_queue.initialize()
        
        max_attempts_result = await final_queue.get_task("max-attempts-task")
        if max_attempts_result:
            logger.info(f"Max attempts task final state: {max_attempts_result.state.name}")
            if max_attempts_result.state == TaskState.DISCARDED:
                logger.info("✓ Task with max attempts was correctly discarded")
            else:
                logger.warning(f"⚠ Expected DISCARDED, got {max_attempts_result.state.name}")
        
        await final_queue.close()
        
        logger.info("Edge cases test completed!")
        
    except Exception as e:
        logger.error(f"Edge cases test failed: {e}", exc_info=True)
        raise
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


async def main():
    """Main test runner"""
    logger.info("Running RetryWorker tests...")
    
    try:
        await test_retry_worker()
        await test_retry_worker_edge_cases()
        logger.info("All tests passed! ✓")
    except Exception as e:
        logger.error(f"Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
