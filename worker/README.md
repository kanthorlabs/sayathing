# Worker Queue Usage Guide

This guide shows how to use the worker queue system for handling TTS processing tasks.

## Quick Start

```python
import asyncio
from worker import WorkerQueue, Task, TaskItem, TaskState, QueueConfig
from tts import TextToSpeechRequest

async def main():
    # Initialize queue with default config (SQLite file in data/ directory)
    config = QueueConfig.from_env()
    queue = WorkerQueue(config)
    await queue.initialize()
    
    try:
        # Create a TTS task
        task_item = TaskItem(
            request=TextToSpeechRequest(
                text="Hello, world!",
                voice_id="kokoro.af_heart"
            ),
            response_url="https://your-webhook.com/callback"
        )
        
        task = Task(
            id="",  # Auto-generated ULID
            state=TaskState.PENDING,
            schedule_at=0,  # Current time
            items=[task_item],
            created_at=0,  # Auto-set
            updated_at=0   # Auto-set
        )
        
        # Enqueue the task
        await queue.enqueue([task])
        
        # Worker dequeues tasks for processing
        tasks = await queue.dequeue(size=5)
        
        for task in tasks:
            try:
                # Process the task (your TTS logic here)
                success = await process_tts_task(task)
                
                if success:
                    await queue.mark_as_complete(task.id)
                else:
                    await queue.mark_as_retry(task.id, "Processing failed")
                    
            except Exception as e:
                await queue.mark_as_retry(task.id, str(e))
        
        # Handle retries
        retry_tasks = await queue.retry(size=10)
        print(f"Processed {len(retry_tasks)} retry tasks")
        
    finally:
        await queue.close()

asyncio.run(main())
```

## Configuration

Configure the queue using environment variables:

```bash
export QUEUE_DATABASE_URL="sqlite+aiosqlite:///data/queue.db"
export QUEUE_MAX_ATTEMPTS="3"
export QUEUE_VISIBILITY_TIMEOUT="3600"  # 1 hour
export QUEUE_RETRY_BACKOFF_MULTIPLIER="2.0"
export QUEUE_RETRY_BASE_DELAY="60"      # 1 minute
export QUEUE_MAX_RETRY_DELAY="3600"     # 1 hour
export QUEUE_BATCH_SIZE="100"
```

Or create a config object:

```python
from worker import QueueConfig

config = QueueConfig(
    database_url="sqlite+aiosqlite:///data/queue.db",
    default_max_attempts=3,
    default_visibility_timeout=3600,
    retry_backoff_multiplier=2.0,
    retry_base_delay=60,
    max_retry_delay=3600,
    batch_size=100
)
```

## Core Operations

### Enqueue Tasks

```python
# Create multiple tasks
tasks = []
for text in ["Hello", "World", "Test"]:
    task_item = TaskItem(
        request=TextToSpeechRequest(text=text, voice_id="kokoro.af_heart"),
        response_url="https://webhook.example.com"
    )
    task = Task(
        id="",  # Auto-generated
        state=TaskState.PENDING,
        schedule_at=0,
        items=[task_item],
        created_at=0,
        updated_at=0
    )
    tasks.append(task)

# Bulk enqueue (atomic operation)
count = await queue.enqueue(tasks)
print(f"Enqueued {count} tasks")
```

### Dequeue Tasks

```python
# Pull tasks for processing
tasks = await queue.dequeue(size=10)

for task in tasks:
    print(f"Processing task {task.id} with {len(task.items)} items")
    # Task is now in PROCESSING state
```

### Handle Task Completion

```python
# Mark task as successfully completed
await queue.mark_as_complete(task_id)

# Mark task for retry with error message
await queue.mark_as_retry(task_id, "Connection timeout")

# Cancel a pending task
await queue.mark_as_cancelled(task_id)

# Discard a failed task
await queue.mark_as_discarded(task_id)

# Resume a discarded task
await queue.mark_as_resume(task_id)
```

### Process Retries

```python
# Handle retry tasks with exponential backoff
retry_tasks = await queue.retry(
    size=10,
    visibility_timeout=3600,  # 1 hour
    max_attempts=3
)

# Tasks with attempt_count >= max_attempts are auto-discarded
```

## Task States

- **PENDING**: Ready for processing
- **PROCESSING**: Currently being processed by a worker
- **COMPLETED**: Successfully processed
- **RETRYABLE**: Failed but eligible for retry
- **CANCELLED**: Manually cancelled
- **DISCARDED**: Failed too many times or manually discarded

## State Transitions

```
PENDING -> PROCESSING (via dequeue)
PROCESSING -> COMPLETED (via mark_as_complete)
PROCESSING -> RETRYABLE (via mark_as_retry)
PROCESSING -> DISCARDED (via mark_as_discarded)
RETRYABLE -> PENDING (via retry, with backoff)
RETRYABLE -> DISCARDED (via retry, when max_attempts exceeded)
PENDING -> CANCELLED (via mark_as_cancelled)
DISCARDED -> PENDING (via mark_as_resume)
```

## Error Handling

```python
from worker import QueueError, TaskNotFoundError, InvalidStateTransitionError

try:
    await queue.mark_as_complete("non-existent-id")
except TaskNotFoundError:
    print("Task not found")

try:
    await queue.mark_as_retry("completed-task-id", "error")
except InvalidStateTransitionError:
    print("Invalid state transition")
```

## Queue Statistics

```python
stats = await queue.get_queue_stats()
print(stats)
# Output: {'pending': 5, 'processing': 2, 'completed': 10, 'total': 17}
```

## Worker Pattern

```python
import asyncio
import logging

async def worker_loop(queue: WorkerQueue, worker_id: str):
    """Simple worker loop"""
    logger = logging.getLogger(f"worker-{worker_id}")
    
    while True:
        try:
            # Dequeue tasks
            tasks = await queue.dequeue(size=5)
            
            if not tasks:
                await asyncio.sleep(1)  # No tasks available
                continue
            
            # Process tasks
            for task in tasks:
                try:
                    success = await process_task(task)
                    if success:
                        await queue.mark_as_complete(task.id)
                        logger.info(f"Completed task {task.id}")
                    else:
                        await queue.mark_as_retry(task.id, "Processing failed")
                        logger.warning(f"Retrying task {task.id}")
                        
                except Exception as e:
                    await queue.mark_as_retry(task.id, str(e))
                    logger.error(f"Error processing task {task.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            await asyncio.sleep(5)  # Back off on errors

async def retry_worker_loop(queue: WorkerQueue):
    """Worker for handling retries"""
    while True:
        try:
            retry_tasks = await queue.retry(size=10)
            if retry_tasks:
                logging.info(f"Processed {len(retry_tasks)} retry tasks")
            await asyncio.sleep(10)  # Check retries every 10 seconds
        except Exception as e:
            logging.error(f"Retry worker error: {e}")
            await asyncio.sleep(30)

# Run multiple workers
async def main():
    queue = WorkerQueue(QueueConfig.from_env())
    await queue.initialize()
    
    # Start workers
    workers = [
        worker_loop(queue, "1"),
        worker_loop(queue, "2"),
        retry_worker_loop(queue)
    ]
    
    await asyncio.gather(*workers)
```

## Best Practices

1. **Use bulk operations**: Enqueue multiple tasks at once for better performance
2. **Handle errors gracefully**: Always wrap task processing in try/catch blocks
3. **Set appropriate timeouts**: Configure visibility timeout based on your processing time
4. **Monitor queue stats**: Check queue statistics regularly for operational insights
5. **Use proper logging**: Log task processing for debugging and monitoring
6. **Implement backoff**: Use exponential backoff for retries to avoid overwhelming the system
7. **Clean up resources**: Always close the queue when done to cleanup database connections
