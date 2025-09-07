"""
Worker Queue implementation with SQLite backend and SQLAlchemy ORM.

This module provides a robust, reliable worker queue system for handling
text-to-speech (TTS) processing tasks with proper error handling, retry
mechanisms, and state management.
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

import ulid
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from .config import QueueConfig
from .database import DatabaseManager, TaskModel
from .task import Task, TaskState

logger = logging.getLogger(__name__)


class QueueError(Exception):
    """Base exception for queue operations"""

    pass


class TaskNotFoundError(QueueError):
    """Raised when a task is not found"""

    pass


class InvalidStateTransitionError(QueueError):
    """Raised when an invalid state transition is attempted"""

    pass


class WorkerQueue:
    """
    A reliable worker queue system backed by SQLite with SQLAlchemy ORM.

    Provides robust task management with:
    - Atomic operations using optimistic concurrency
    - Visibility timeout to prevent duplicate processing
    - Pull-based model for worker task retrieval
    - Bulk operations for efficient batch processing
    - Retry mechanisms with exponential backoff
    - Comprehensive state management
    """

    def __init__(self, config: Optional[QueueConfig] = None, database_manager: Optional[DatabaseManager] = None):
        self.config = config or QueueConfig.from_env()
        if database_manager is None:
            # Fallback to creating our own DatabaseManager if not injected
            self.db_manager = DatabaseManager(self.config.database_url)
        else:
            self.db_manager = database_manager

    async def initialize(self):
        """Initialize the queue and create database tables"""
        await self.db_manager.create_tables()
        logger.info("Worker queue initialized with database: %s", self.config.database_url)

    async def close(self):
        """Close the queue and cleanup resources"""
        await self.db_manager.close()
        logger.info("Worker queue closed")

    @asynccontextmanager
    async def _get_session(self):
        """Context manager for database sessions with proper error handling"""
        session = await self.db_manager.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def _current_timestamp_ms(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)

    def _calculate_retry_delay(self, attempt_count: int) -> int:
        """Calculate exponential backoff delay in milliseconds"""
        delay_seconds = min(
            self.config.retry_base_delay * (self.config.retry_backoff_multiplier**attempt_count),
            self.config.max_retry_delay,
        )
        return int(delay_seconds * 1000)

    async def enqueue(self, tasks: List[Task]) -> List[str]:
        """
        Bulk insert multiple tasks atomically.

        Args:
            tasks: List of tasks to enqueue

        Returns:
            Number of tasks successfully enqueued

        Raises:
            QueueError: If bulk insertion fails
        """
        if not tasks:
            return []

        current_time = self._current_timestamp_ms()

        # Prepare task models for bulk insertion
        task_models = []
        for task in tasks:
            # Generate ULID if not provided
            if not task.id:
                task.id = str(ulid.new())

            # Set timestamps
            task.created_at = current_time
            task.updated_at = current_time

            # Default schedule_at to current time if not set
            if not task.schedule_at:
                task.schedule_at = current_time

            task_models.append(TaskModel.from_task(task))

        async with self._get_session() as session:
            try:
                # Use bulk insert with ON CONFLICT IGNORE for duplicate IDs
                session.add_all(task_models)
                await session.flush()

                logger.info("Enqueued %d tasks", len(tasks))
                return [task.id for task in tasks]

            except IntegrityError as e:
                logger.warning("Some tasks may have duplicate IDs: %s", e)
                # Count how many were actually inserted by checking existing IDs
                task_ids = [task.id for task in tasks]
                result = await session.execute(select(TaskModel.id).where(TaskModel.id.in_(task_ids)))
                return [row.id for row in result.fetchall()]

            except Exception as e:
                logger.error("Failed to enqueue tasks: %s", e)
                raise QueueError(f"Failed to enqueue tasks: {e}")

    async def dequeue(self, size: int = 5) -> List[Task]:
        """
        Pull-based model to retrieve tasks for processing.

        Uses atomic CTE with UPDATE...RETURNING for race-condition safety.

        Args:
            size: Maximum number of tasks to retrieve

        Returns:
            List of tasks ready for processing
        """
        if size <= 0:
            return []

        current_time = self._current_timestamp_ms()

        async with self._get_session() as session:
            try:
                # Use raw SQL for atomic CTE operation
                query = text(
                    """
                    WITH selected_tasks AS (
                        SELECT id FROM tasks
                        WHERE state = :pending_state AND schedule_at <= :current_time
                        ORDER BY created_at ASC
                        LIMIT :limit_size
                    )
                    UPDATE tasks SET
                        state = :processing_state,
                        updated_at = :current_time
                    WHERE id IN (SELECT id FROM selected_tasks)
                        AND state = :pending_state
                    RETURNING *
                """
                )

                result = await session.execute(
                    query,
                    {
                        "pending_state": TaskState.PENDING.value,
                        "processing_state": TaskState.PROCESSING.value,
                        "current_time": current_time,
                        "limit_size": size,
                    },
                )

                # Convert results to Task objects
                tasks = []
                for row in result.fetchall():
                    task_model = TaskModel(
                        id=row.id,
                        state=row.state,
                        schedule_at=row.schedule_at,
                        attempt_count=row.attempt_count,
                        attempted_at=row.attempted_at,
                        attempted_error=row.attempted_error,
                        finalized_at=row.finalized_at,
                        items=row.items,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                    tasks.append(task_model.to_task())

                logger.info("Dequeued %d tasks for processing", len(tasks))
                return tasks

            except Exception as e:
                logger.error("Failed to dequeue tasks: %s", e)
                raise QueueError(f"Failed to dequeue tasks: {e}")

    async def retry(
        self, size: int = 5, visibility_timeout: Optional[int] = None, max_attempts: Optional[int] = None
    ) -> List[Task]:
        """
        Pull-based retry with configurable timeout.

        Finds tasks that need retry and processes them with exponential backoff.

        Args:
            size: Maximum number of tasks to retry
            visibility_timeout: Timeout in seconds for stale PROCESSING tasks
            max_attempts: Maximum retry attempts before discarding

        Returns:
            List of tasks moved to RETRYABLE or auto-discarded
        """
        if size <= 0:
            return []

        visibility_timeout = visibility_timeout or self.config.default_visibility_timeout
        max_attempts = max_attempts or self.config.default_max_attempts
        current_time = self._current_timestamp_ms()
        visibility_timeout_ms = visibility_timeout * 1000
        stale_cutoff = current_time - visibility_timeout_ms

        async with self._get_session() as session:
            try:
                # Calculate retry delays for different attempt counts
                retry_delays = {}
                for attempt in range(max_attempts):
                    retry_delays[attempt] = self._calculate_retry_delay(attempt)

                # Build CASE statement for schedule_at calculation
                schedule_case_parts = []
                for attempt in range(max_attempts - 1):  # Don't need delay for max attempts (will be discarded)
                    delay_ms = retry_delays[attempt]
                    schedule_case_parts.append(
                        f"WHEN (attempt_count + 1) = {attempt + 1} THEN {current_time + delay_ms}"
                    )

                schedule_case = "CASE " + " ".join(schedule_case_parts) + f" ELSE {current_time} END"

                # Single atomic query to update all fields including schedule_at
                query = text(
                    f"""
                    WITH selected_tasks AS (
                        SELECT id, attempt_count FROM tasks
                        WHERE (
                            (state = :retryable_state) OR
                            (state = :processing_state AND schedule_at < :stale_cutoff)
                        )
                        AND schedule_at <= :current_time
                        AND attempt_count < :max_attempts
                        ORDER BY created_at ASC
                        LIMIT :limit_size
                    )
                    UPDATE tasks SET
                        state = CASE
                            WHEN (attempt_count + 1) >= :max_attempts THEN :discarded_state
                            ELSE :pending_state
                        END,
                        schedule_at = CASE
                            WHEN (attempt_count + 1) >= :max_attempts THEN schedule_at
                            ELSE {schedule_case}
                        END,
                        finalized_at = CASE
                            WHEN (attempt_count + 1) >= :max_attempts THEN :current_time
                            ELSE finalized_at
                        END,
                        attempt_count = attempt_count + 1,
                        attempted_at = :current_time,
                        updated_at = :current_time
                    WHERE id IN (SELECT id FROM selected_tasks)
                    AND (
                        (state = :retryable_state) OR
                        (state = :processing_state AND schedule_at < :stale_cutoff)
                    )
                    RETURNING *
                """
                )

                result = await session.execute(
                    query,
                    {
                        "retryable_state": TaskState.RETRYABLE.value,
                        "processing_state": TaskState.PROCESSING.value,
                        "pending_state": TaskState.PENDING.value,
                        "discarded_state": TaskState.DISCARDED.value,
                        "current_time": current_time,
                        "stale_cutoff": stale_cutoff,
                        "max_attempts": max_attempts,
                        "limit_size": size,
                    },
                )

                # Convert results to Task objects
                tasks = []
                for row in result.fetchall():
                    task_model = TaskModel(
                        id=row.id,
                        state=row.state,
                        schedule_at=row.schedule_at,
                        attempt_count=row.attempt_count,
                        attempted_at=row.attempted_at,
                        attempted_error=row.attempted_error,
                        finalized_at=row.finalized_at,
                        items=row.items,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                    task = task_model.to_task()
                    tasks.append(task)

                    # Log the action taken
                    if task_model.state == TaskState.DISCARDED.value:  # type: ignore
                        logger.debug(
                            "Auto-discarded task %s after %d attempts", task_model.id, task_model.attempt_count
                        )
                    else:
                        retry_delay = task_model.schedule_at - current_time
                        logger.debug("Scheduled retry for task %s in %d ms", task_model.id, retry_delay)

                logger.info("Processed %d tasks for retry", len(tasks))
                return tasks

            except Exception as e:
                logger.error("Failed to retry tasks: %s", e)
                raise QueueError(f"Failed to retry tasks: {e}")

    async def mark_as_complete(self, task: Task) -> Task:
        """
        Transition task from PROCESSING to COMPLETED with updated items.

        Args:
            task: Task object to mark as complete (with updated items)

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If task is not in PROCESSING state
        """
        async with self._get_session() as session:
            # Get current task from database
            result = await session.execute(select(TaskModel).where(TaskModel.id == task.id))
            task_model = result.scalar_one_or_none()

            if not task_model:
                raise TaskNotFoundError(f"Task {task.id} not found")

            # Validate state transition
            if task_model.state != TaskState.PROCESSING.value:  # type: ignore
                current_state = TaskState(task_model.state)  # type: ignore
                raise InvalidStateTransitionError(
                    f"Cannot mark task {task.id} as complete: " f"expected PROCESSING, got {current_state.name}"
                )

            # Update task using SQLAlchemy update statement
            current_time = self._current_timestamp_ms()
            await session.execute(
                update(TaskModel)
                .where(TaskModel.id == task.id)
                .values(
                    state=TaskState.COMPLETED.value,
                    items=json.dumps([item.model_dump() for item in task.items]),
                    finalized_at=current_time,
                    updated_at=current_time,
                )
            )

            await session.flush()

            # Fetch updated task
            result = await session.execute(select(TaskModel).where(TaskModel.id == task.id))
            updated_task_model = result.scalar_one()

            logger.info("Marked task %s as complete with %d items", task.id, len(task.items))
            return updated_task_model.to_task()

    async def mark_as_retry(self, task_id: str, error: str) -> Task:
        """
        Transition task from PROCESSING to RETRYABLE with error logging.

        Args:
            task_id: ID of the task to mark for retry
            error: Error message to log

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If task is not in PROCESSING state
        """
        async with self._get_session() as session:
            # Get current task
            result = await session.execute(select(TaskModel).where(TaskModel.id == task_id))
            task_model = result.scalar_one_or_none()

            if not task_model:
                raise TaskNotFoundError(f"Task {task_id} not found")

            if task_model.state != TaskState.PROCESSING.value:  # type: ignore
                raise InvalidStateTransitionError(
                    f"Cannot mark task {task_id} as retry: expected PROCESSING, got {TaskState(task_model.state).name}"  # type: ignore
                )

            # Parse existing errors and add new one
            existing_errors_json = task_model.attempted_error or "[]"  # type: ignore
            existing_errors = json.loads(existing_errors_json)  # type: ignore
            existing_errors.append(error)

            # Update task using SQLAlchemy update statement
            current_time = self._current_timestamp_ms()
            await session.execute(
                update(TaskModel)
                .where(TaskModel.id == task_id)
                .values(
                    state=TaskState.RETRYABLE.value,
                    attempted_error=json.dumps(existing_errors),
                    updated_at=current_time,
                )
            )

            await session.flush()

            # Fetch updated task
            result = await session.execute(select(TaskModel).where(TaskModel.id == task_id))
            updated_task_model = result.scalar_one()

            logger.info("Marked task %s for retry with error: %s", task_id, error)
            return updated_task_model.to_task()

    async def mark_as_cancelled(self, task_id: str) -> Task:
        """
        Transition task from PENDING to CANCELLED.

        Args:
            task_id: ID of the task to cancel

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If task is not in PENDING state
        """
        return await self._update_task_state(
            task_id, TaskState.CANCELLED, expected_state=TaskState.PENDING, finalize=True
        )

    async def mark_as_discarded(self, task_id: str) -> Task:
        """
        Transition task from PROCESSING to DISCARDED.

        Args:
            task_id: ID of the task to discard

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If task is not in PROCESSING state
        """
        return await self._update_task_state(
            task_id, TaskState.DISCARDED, expected_state=TaskState.PROCESSING, finalize=True
        )

    async def mark_as_resume(self, task_id: str) -> Task:
        """
        Transition task from DISCARDED to PENDING.

        Args:
            task_id: ID of the task to resume

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If task is not in DISCARDED state
        """
        return await self._update_task_state(
            task_id, TaskState.PENDING, expected_state=TaskState.DISCARDED, reset_schedule=True
        )

    async def _update_task_state(
        self,
        task_id: str,
        new_state: TaskState,
        expected_state: Optional[TaskState] = None,
        finalize: bool = False,
        reset_schedule: bool = False,
    ) -> Task:
        """
        Helper method for atomic task state updates.

        Args:
            task_id: ID of the task to update
            new_state: New state to set
            expected_state: Expected current state (for validation)
            finalize: Whether to set finalized_at timestamp
            reset_schedule: Whether to reset schedule_at to current time

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If state transition is invalid
        """
        async with self._get_session() as session:
            # Get current task
            result = await session.execute(select(TaskModel).where(TaskModel.id == task_id))
            task_model = result.scalar_one_or_none()

            if not task_model:
                raise TaskNotFoundError(f"Task {task_id} not found")

        # Validate state transition if expected state is provided
        if expected_state and task_model.state != expected_state.value:  # type: ignore
            current_state = TaskState(task_model.state)  # type: ignore
            raise InvalidStateTransitionError(
                f"Cannot transition task {task_id} to {new_state.name}: "
                f"expected {expected_state.name}, got {current_state.name}"
            )

        # Prepare update values
        current_time = self._current_timestamp_ms()
        update_values = {"state": new_state.value, "updated_at": current_time}

        if finalize:
            update_values["finalized_at"] = current_time

        if reset_schedule:
            update_values["schedule_at"] = current_time

        # Update task using SQLAlchemy update statement
        await session.execute(update(TaskModel).where(TaskModel.id == task_id).values(**update_values))

        await session.flush()

        # Fetch updated task
        result = await session.execute(select(TaskModel).where(TaskModel.id == task_id))
        updated_task_model = result.scalar_one()

        logger.info("Updated task %s state to %s", task_id, new_state.name)
        return updated_task_model.to_task()

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task if found, None otherwise
        """
        async with self._get_session() as session:
            result = await session.execute(select(TaskModel).where(TaskModel.id == task_id))
            task_model = result.scalar_one_or_none()

            if task_model:
                return task_model.to_task()
            return None
