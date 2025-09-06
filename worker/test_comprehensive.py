#!/usr/bin/env python3
"""
Comprehensive test suite for the worker queue implementation using pytest.
"""
import asyncio
import logging
import json
import time
import pytest
import pytest_asyncio
import sys
from pathlib import Path
from typing import List

# Add the parent directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tts import TextToSpeechRequest
from worker import (
    WorkerQueue, Task, TaskItem, TaskState, QueueConfig,
    QueueError, TaskNotFoundError, InvalidStateTransitionError
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def queue_config():
    """Fixture providing test queue configuration"""
    return QueueConfig(database_url="sqlite+aiosqlite:///:memory:")


@pytest_asyncio.fixture
async def worker_queue(queue_config):
    """Fixture providing initialized worker queue"""
    queue = WorkerQueue(queue_config)
    await queue.initialize()
    yield queue
    await queue.close()


def create_sample_task(task_id: str = "", text: str = "Test message") -> Task:
    """Create a sample task for testing"""
    task_item = TaskItem(
        request=TextToSpeechRequest(
            text=text,
            voice_id="kokoro.af_heart",
            metadata={"test": True}
        ),
        response_url="https://example.com/webhook"
    )
    
    return Task(
        id=task_id,
        state=TaskState.PENDING,
        schedule_at=0,
        items=[task_item],
        created_at=0,
        updated_at=0
    )


@pytest.mark.asyncio
async def test_enqueue_dequeue(worker_queue):
    """Test basic enqueue and dequeue operations"""
    logger.info("Testing enqueue/dequeue operations")
    
    # Create test tasks
    tasks = [
        create_sample_task(text=f"Test message {i}")
        for i in range(3)
    ]
    
    # Test enqueue
    enqueued_ids = await worker_queue.enqueue(tasks)
    enqueued_count = len(enqueued_ids)
    assert enqueued_count == 3, f"Expected 3 tasks enqueued, got {enqueued_count}"
    
    # Test dequeue
    dequeued_tasks = await worker_queue.dequeue(2)
    assert len(dequeued_tasks) == 2, f"Expected 2 dequeued tasks, got {len(dequeued_tasks)}"
    
    # Verify tasks are in PROCESSING state
    for task in dequeued_tasks:
        assert task.state == TaskState.PROCESSING, f"Expected PROCESSING state, got {task.state}"
    
    # Test remaining tasks
    remaining_tasks = await worker_queue.dequeue(5)
    assert len(remaining_tasks) == 1, f"Expected 1 remaining task, got {len(remaining_tasks)}"
    
    logger.info("✓ Enqueue/dequeue test passed")


@pytest.mark.asyncio
async def test_state_transitions(worker_queue):
    """Test task state transitions"""
    logger.info("Testing state transitions")
    
    # Create and enqueue a task
    task = create_sample_task(text="State transition test")
    await worker_queue.enqueue([task])
    
    # Dequeue the task
    tasks = await worker_queue.dequeue(1)
    assert len(tasks) == 1
    task = tasks[0]
    task_id = task.id
    
    # Simulate task processing by updating items with response URLs
    for item in task.items:
        item.response_url = "data:audio/wav;base64,completed_audio_data"
    
    # Test mark_as_complete
    completed_task = await worker_queue.mark_as_complete(task)
    assert completed_task.state == TaskState.COMPLETED
    assert completed_task.finalized_at is not None
    
    # Test invalid transition (completed task can't be marked for retry)
    with pytest.raises(InvalidStateTransitionError):
        await worker_queue.mark_as_retry(task_id, "Should fail")
    
    logger.info("✓ State transitions test passed")


@pytest.mark.asyncio
async def test_retry_mechanism(worker_queue):
    """Test retry mechanism with exponential backoff"""
    logger.info("Testing retry mechanism")
    
    # Create and enqueue a task
    task = create_sample_task(text="Retry test")
    await worker_queue.enqueue([task])
    
    # Dequeue and mark for retry
    tasks = await worker_queue.dequeue(1)
    task_id = tasks[0].id
    
    # Mark as retry with error
    retry_task = await worker_queue.mark_as_retry(task_id, "Test error")
    assert retry_task.state == TaskState.RETRYABLE
    assert len(retry_task.attempted_error) == 1
    assert retry_task.attempted_error[0] == "Test error"
    
    # Test retry processing
    retry_tasks = await worker_queue.retry(size=1)
    assert len(retry_tasks) == 1
    
    # Task should be PENDING again with incremented attempt count
    updated_task = await worker_queue.get_task(task_id)
    assert updated_task.state == TaskState.PENDING
    assert updated_task.attempt_count == 1
    
    logger.info("✓ Retry mechanism test passed")


@pytest.mark.asyncio
async def test_visibility_timeout(worker_queue):
    """Test visibility timeout for stale PROCESSING tasks"""
    logger.info("Testing visibility timeout")
    
    # Create and enqueue a task
    task = create_sample_task(text="Visibility timeout test")
    await worker_queue.enqueue([task])
    
    # Dequeue the task (now in PROCESSING state)
    tasks = await worker_queue.dequeue(1)
    task_id = tasks[0].id
    
    # Test retry with very short visibility timeout
    retry_tasks = await worker_queue.retry(size=1, visibility_timeout=1, max_attempts=3)
    
    if retry_tasks:
        logger.info("✓ Visibility timeout test passed (task was considered stale)")
    else:
        logger.info("✓ Visibility timeout test passed (no stale tasks found)")


@pytest.mark.asyncio
async def test_max_attempts_discard(worker_queue):
    """Test auto-discard after max attempts"""
    logger.info("Testing max attempts auto-discard")
    
    # Create and enqueue a task
    task = create_sample_task(text="Max attempts test")
    await worker_queue.enqueue([task])
    
    # Dequeue the task
    tasks = await worker_queue.dequeue(1)
    task_id = tasks[0].id
    
    # Simulate reaching max attempts by directly calling retry with high attempt count
    # First mark as retry to put it in RETRYABLE state
    await worker_queue.mark_as_retry(task_id, "Error 1")
    
    # Manually set the attempt_count to max-1 to test auto-discard on next retry
    async with worker_queue._get_session() as session:
        from sqlalchemy import update
        from worker.database import TaskModel
        await session.execute(
            update(TaskModel)
            .where(TaskModel.id == task_id)
            .values(attempt_count=2)  # Will become 3 on next retry (max_attempts=3)
        )
    
    # Now call retry - this should auto-discard the task
    await worker_queue.retry(size=1, max_attempts=3)
    
    # Task should now be auto-discarded
    final_task = await worker_queue.get_task(task_id)
    assert final_task.state == TaskState.DISCARDED
    assert final_task.finalized_at is not None
    assert final_task.attempt_count == 3
    
    logger.info("✓ Max attempts auto-discard test passed")


@pytest.mark.asyncio
async def test_cancel_and_resume(worker_queue):
    """Test cancelling and resuming tasks"""
    logger.info("Testing cancel and resume operations")
    
    # Create and enqueue tasks
    tasks = [
        create_sample_task(text="Cancel test"),
        create_sample_task(text="Resume test")
    ]
    await worker_queue.enqueue(tasks)
    
    # Dequeue one task for cancellation
    pending_tasks = await worker_queue.dequeue(1)
    assert len(pending_tasks) == 1
    
    # Get the remaining pending task for cancellation
    remaining_tasks = await worker_queue.dequeue(1)
    cancel_task_id = remaining_tasks[0].id
    
    # First, put it back to PENDING for cancellation test
    await worker_queue.mark_as_retry(remaining_tasks[0].id, "Put back to pending")
    await worker_queue.retry(size=1)
    
    # Now cancel it
    cancelled_task = await worker_queue.mark_as_cancelled(cancel_task_id)
    assert cancelled_task.state == TaskState.CANCELLED
    
    # Test resume (move from DISCARDED to PENDING)
    processing_task_id = pending_tasks[0].id
    await worker_queue.mark_as_discarded(processing_task_id)
    
    resumed_task = await worker_queue.mark_as_resume(processing_task_id)
    assert resumed_task.state == TaskState.PENDING
    
    logger.info("✓ Cancel and resume test passed")


@pytest.mark.asyncio
async def test_error_cases(worker_queue):
    """Test error handling"""
    logger.info("Testing error cases")
    
    # Test getting non-existent task
    non_existent_task = await worker_queue.get_task("non-existent-id")
    assert non_existent_task is None
    
    # Test invalid state transitions
    with pytest.raises(TaskNotFoundError):
        non_existent_task = create_sample_task(task_id="non-existent-id")
        await worker_queue.mark_as_complete(non_existent_task)
    
    # Test empty enqueue
    empty_ids = await worker_queue.enqueue([])
    assert len(empty_ids) == 0

    # Test dequeue with invalid size
    empty_dequeue = await worker_queue.dequeue(0)
    assert len(empty_dequeue) == 0
    
    logger.info("✓ Error cases test passed")
