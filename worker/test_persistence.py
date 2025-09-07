#!/usr/bin/env python3
"""
Test script to verify queue persistence with file-based SQLite database.
"""
import asyncio
import logging
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add the parent directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tts import TextToSpeechRequest
from worker import WorkerQueue, Task, TaskItem, TaskState, QueueConfig
from container import create_test_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_queue_persistence():
    """Test that the queue persists data correctly to disk"""
    
    # Create a temporary directory for the test database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_queue.db")
        config = QueueConfig(database_url=f"sqlite+aiosqlite:///{db_path}")
        
        # Phase 1: Create queue and add tasks
        logger.info("Phase 1: Creating queue and adding tasks")
        test_container1 = create_test_container(config)
        queue1 = test_container1.worker_queue()
        await queue1.initialize()
        
        # Create a test task
        task_item = TaskItem(
            request=TextToSpeechRequest(
                text="Test persistence message",
                voice_id="kokoro.af_heart"
            ),
            response_url="https://example.com/webhook"
        )
        
        task = Task(
            id="",  # Auto-generated
            state=TaskState.PENDING,
            schedule_at=0,
            items=[task_item],
            created_at=0,
            updated_at=0
        )
        
        await queue1.enqueue([task])
        logger.info("Enqueued 1 task")
        
        # Get the task ID for later reference
        tasks = await queue1.dequeue(1)
        assert len(tasks) == 1, "Should dequeue exactly 1 task"
        task_id = tasks[0].id
        logger.info("Dequeued task: %s", task_id)
        assert tasks[0].state == TaskState.PROCESSING, "Dequeued task should be in PROCESSING state"
            
        await queue1.close()
        
        # Phase 2: Recreate queue and verify persistence
        logger.info("Phase 2: Recreating queue and verifying persistence")
        test_container2 = create_test_container(config)
        queue2 = test_container2.worker_queue()
        await queue2.initialize()
        
        # Verify the task is still there
        retrieved_task = await queue2.get_task(task_id)
        assert retrieved_task is not None, "Task should persist after queue restart"
        assert retrieved_task.id == task_id, "Retrieved task should have the same ID"
        assert retrieved_task.state == TaskState.PROCESSING, "Retrieved task should maintain its state"
        
        logger.info("Successfully retrieved persisted task: %s (state: %s)", 
                   retrieved_task.id, retrieved_task.state.name)
        
        await queue2.close()
        logger.info("Test completed - temporary database will be automatically cleaned up")
