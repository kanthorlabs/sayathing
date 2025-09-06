"""
Worker queue package for handling TTS processing tasks.

This package provides a robust, reliable worker queue system backed by SQLite
with SQLAlchemy ORM for handling text-to-speech processing tasks.
"""

from .queue import WorkerQueue, QueueError, TaskNotFoundError, InvalidStateTransitionError
from .task import Task, TaskItem, TaskState
from .config import QueueConfig, WorkerConfig
from .database import DatabaseManager, TaskModel
from .workers import PrimaryWorker, RetryWorker
from .container import container, create_test_container, initialize_container

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
    "container",
    "create_test_container",
    "initialize_container",
]
