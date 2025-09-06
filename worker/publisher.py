"""Publisher abstraction for creating tasks in the worker queue.

The Publisher provides a simple interface for publishing many TTS tasks at
once. It wraps the underlying `WorkerQueue` so API layers don't need to know
about low-level task construction details.
"""
from __future__ import annotations

from typing import List

from .queue import WorkerQueue
from .task import Task, TaskItem, TaskState


class Publisher:
    """High level publisher that batches task publishing to the queue.

    Usage::

        publisher = Publisher(worker_queue)
        task_ids = await publisher.pub([TaskItem(...), TaskItem(...)])
    """

    def __init__(self, queue: WorkerQueue):
        self._queue = queue

    async def pub(self, items: List[TaskItem]) -> List[str]:
        """Publish many task items at once.

        Each item becomes its own Task (1 item per task) so retries and
        lifecycle management are isolated. Returns the list of generated
        task IDs (ULIDs).
        """
        if not items:
            return []

        tasks: List[Task] = [
            Task(
                id="",  # let queue assign ULID
                state=TaskState.PENDING,
                schedule_at=0,  # will be set by queue
                items=items,
                created_at=0,
                updated_at=0,
            )
        ]
        
        return await self._queue.enqueue(tasks)
