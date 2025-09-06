"""
Configuration for the worker queue system.
"""
import os
from dataclasses import dataclass


@dataclass
class QueueConfig:
    """Configuration settings for the worker queue"""
    database_url: str = "sqlite+aiosqlite:///data/queue.db"
    default_max_attempts: int = 3
    default_visibility_timeout: int = 3600  # 1 hour in seconds
    retry_backoff_multiplier: float = 2.0
    retry_base_delay: int = 60  # 1 minute in seconds
    max_retry_delay: int = 3600  # 1 hour in seconds
    batch_size: int = 100

    @classmethod
    def from_env(cls) -> "QueueConfig":
        """Create configuration from environment variables"""
        return cls(
            database_url=os.getenv("QUEUE_DATABASE_URL", "sqlite+aiosqlite:///data/queue.db"),
            default_max_attempts=int(os.getenv("QUEUE_MAX_ATTEMPTS", "3")),
            default_visibility_timeout=int(os.getenv("QUEUE_VISIBILITY_TIMEOUT", "3600")),
            retry_backoff_multiplier=float(os.getenv("QUEUE_RETRY_BACKOFF_MULTIPLIER", "2.0")),
            retry_base_delay=int(os.getenv("QUEUE_RETRY_BASE_DELAY", "60")),
            max_retry_delay=int(os.getenv("QUEUE_MAX_RETRY_DELAY", "3600")),
            batch_size=int(os.getenv("QUEUE_BATCH_SIZE", "100"))
        )


@dataclass
class WorkerConfig:
    """Configuration settings for workers"""
    # Primary worker settings
    worker_poll_delay: int = 5  # seconds
    worker_batch_size: int = 5
    
    # Retry worker settings
    retry_worker_poll_delay: int = 30  # seconds - longer delay for retries
    retry_worker_batch_size: int = 5
    retry_worker_visibility_timeout: int = 3600  # 1 hour
    retry_worker_max_attempts: int = 3

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Create configuration from environment variables"""
        return cls(
            worker_poll_delay=int(os.getenv("WORKER_POLL_DELAY", "5")),
            worker_batch_size=int(os.getenv("WORKER_BATCH_SIZE", "5")),
            retry_worker_poll_delay=int(os.getenv("RETRY_WORKER_POLL_DELAY", "30")),
            retry_worker_batch_size=int(os.getenv("RETRY_WORKER_BATCH_SIZE", "5")),
            retry_worker_visibility_timeout=int(os.getenv("RETRY_WORKER_VISIBILITY_TIMEOUT", "3600")),
            retry_worker_max_attempts=int(os.getenv("RETRY_WORKER_MAX_ATTEMPTS", "3"))
        )
