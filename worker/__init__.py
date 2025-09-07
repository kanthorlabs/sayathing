"""
Worker queue package for handling TTS processing tasks.

This package provides a robust, reliable worker queue system backed by SQLite
with SQLAlchemy ORM for handling text-to-speech processing tasks.
"""

from .config import QueueConfig, WorkerConfig
from .database import DatabaseManager, TaskModel
from .queue import (InvalidStateTransitionError, QueueError, TaskNotFoundError,
                    WorkerQueue)
from .task import Task, TaskItem, TaskState
from .workers import PrimaryWorker, RetryWorker

__all__ = [
    "WorkerQueue",
    "QueueError",
    "TaskNotFoundError",
    "InvalidStateTransitionError",
    "Task",
    "TaskItem",
    "TaskState",
    "QueueConfig",
    "WorkerConfig",
    "DatabaseManager",
    "TaskModel",
    "PrimaryWorker",
    "RetryWorker",
]
