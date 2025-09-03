# Worker Queue Implementation Plan

## Overview

This document outlines the implementation of a simple, reliable worker queue system backed by SQLite with SQLAlchemy ORM. The queue handles text-to-speech (TTS) processing tasks with robust error handling, retry mechanisms, and state management.

## Core Requirements

### Queue Operations
- `enqueue(tasks: List[Task])`: Bulk insert multiple tasks atomically
- `dequeue(size: int = 5)`: Pull-based model to retrieve X tasks for processing  
- `retry(size: int = 5, visibility_timeout: int = 3600, max_attempts: int = 3)`: Pull-based retry with configurable timeout
- `mark_as_complete(task_id: str)`: Transition task from PROCESSING to COMPLETED
- `mark_as_retry(task_id: str, error: str)`: Transition task from PROCESSING to RETRYABLE with error logging
- `mark_as_cancelled(task_id: str)`: Transition task from PENDING to CANCELLED
- `mark_as_discarded(task_id: str)`: Transition task from PROCESSING to DISCARDED
- `mark_as_resume(task_id: str)`: Transition task from DISCARDED to PENDING

### Key Design Principles
- **Optimistic Concurrency**: Use atomic updates to avoid lost updates
- **Visibility Timeout**: Prevent task duplication during processing using `schedule_at + visibility_timeout`
- **Pull-Based Model**: Workers actively request tasks rather than receiving pushes
- **Bulk Operations**: Efficient batch processing for better performance
- **ULID Primary Keys**: Use `ulid-py` for sortable, unique identifiers

## Database Schema

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- ULID for sortable unique IDs
    state INTEGER NOT NULL,           -- TaskState enum value
    schedule_at INTEGER NOT NULL,     -- Unix timestamp (milliseconds)
    attempt_count INTEGER DEFAULT 0,  -- Number of processing attempts
    attempted_at INTEGER,             -- Last attempt timestamp
    attempted_error TEXT,             -- JSON array of error messages
    finalized_at INTEGER,             -- Completion/discard timestamp
    items TEXT NOT NULL,              -- JSON serialized TaskItem list
    created_at INTEGER NOT NULL,      -- Creation timestamp
    updated_at INTEGER NOT NULL       -- Last update timestamp
);

-- Indexes for performance
CREATE INDEX idx_tasks_state_schedule ON tasks(state, schedule_at);
CREATE INDEX idx_tasks_created ON tasks(created_at);
```

## Implementation Strategy

### 1. Enqueue Operation
- Use SQLAlchemy's `bulk_insert_mappings()` for performance
- Handle duplicate IDs with `ON CONFLICT IGNORE`
- Validate task data before insertion
- Set timestamps: `created_at`, `updated_at`, `schedule_at`

### 2. Dequeue Operation  
- Use Common Table Expression (CTE) with `UPDATE...RETURNING` for atomicity
- Query: `WHERE state = PENDING AND schedule_at <= now() ORDER BY created_at ASC LIMIT size`
- Update matching tasks to `PROCESSING` state
- Return only successfully updated tasks to avoid race conditions

### 3. Retry Operation
- Find tasks needing retry: `state = RETRYABLE OR (state = PROCESSING AND schedule_at + visibility_timeout < now())`
- Filter by `attempt_count < max_attempts`
- Increment `attempt_count`, update `schedule_at` with exponential backoff
- Auto-discard tasks exceeding `max_attempts`

### 4. State Transitions
- Implement atomic updates with proper state validation
- Log errors in `attempted_error` as JSON array
- Update timestamps appropriately for each transition

## Key Implementation Details

### Visibility Timeout Logic
```python
# Check if PROCESSING task has timed out
current_time = int(time.time() * 1000)
is_stale = task.schedule_at + (visibility_timeout * 1000) < current_time
```

### Exponential Backoff
```python
# Calculate next retry delay
delay = min(base_delay * (multiplier ** attempt_count), max_delay)
next_schedule_at = current_time + delay
```

### Atomic Updates Pattern
```sql
-- Example for dequeue operation
WITH selected_tasks AS (
    SELECT id FROM tasks 
    WHERE state = ? AND schedule_at <= ?
    ORDER BY created_at ASC 
    LIMIT ?
)
UPDATE tasks SET 
    state = ?, 
    updated_at = ?
WHERE id IN (SELECT id FROM selected_tasks)
RETURNING *;
```

## Configuration

```python
@dataclass
class QueueConfig:
    database_url: str = "sqlite:///data/queue.db"
    default_max_attempts: int = 3
    default_visibility_timeout: int = 3600  # 1 hour
    retry_backoff_multiplier: float = 2.0
    retry_base_delay: int = 60  # 1 minute
    max_retry_delay: int = 3600  # 1 hour
    batch_size: int = 100
```

## Error Handling & Edge Cases

### Concurrency
- Use transaction isolation levels appropriately
- Handle deadlocks with retry logic
- Implement proper connection pooling

### Data Integrity  
- Validate state transitions before updates
- Handle malformed JSON in task items/errors
- Implement cleanup for orphaned tasks

### Performance
- Use prepared statements for repeated queries
- Implement pagination for large result sets
- Monitor index usage and query performance

## Dependencies

```toml
dependencies = [
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",  # For async SQLite support
    "ulid-py>=1.1.0",
    "pydantic>=2.0.0",
]
```

## Implementation Phases

1. **Core CRUD**: Basic enqueue/dequeue with state management
2. **Reliability**: Visibility timeout, retry logic, error handling  
3. **Monitoring**: Queue statistics, health checks
4. **Optimization**: Performance tuning, cleanup operations

