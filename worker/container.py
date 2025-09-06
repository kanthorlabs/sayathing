"""
Dependency injection container for the worker system.

This module uses python-dependency-injector to manage dependencies
and ensure proper singleton behavior for shared resources like DatabaseManager.
"""

from dependency_injector import containers, providers

from .config import QueueConfig, WorkerConfig
from .database import DatabaseManager
from .queue import WorkerQueue


class Container(containers.DeclarativeContainer):
    """Main dependency injection container"""
    
    # Configuration providers
    queue_config = providers.Singleton(
        QueueConfig.from_env
    )
    
    worker_config = providers.Singleton(
        WorkerConfig.from_env
    )
    
    # Database manager as singleton - this ensures only one instance across the entire app
    database_manager = providers.Singleton(
        DatabaseManager,
        database_url=queue_config.provided.database_url
    )
    
    # Worker queue with injected database manager
    worker_queue = providers.Factory(
        WorkerQueue,
        config=queue_config,
        database_manager=database_manager
    )


def create_test_container(queue_config: QueueConfig) -> Container:
    """Create a test container with custom configuration"""
    test_container = Container()
    test_container.queue_config.override(providers.Object(queue_config))
    test_container.worker_config.override(providers.Singleton(WorkerConfig.from_env))
    return test_container


# Global container instance - this ensures all components use the same singleton instances
container = Container()

# Initialize the container to ensure all singletons are created
async def initialize_container():
    """Initialize the container and its singletons"""
    # This ensures the database manager singleton is created early
    db_manager = container.database_manager()
    await db_manager.initialize()
    return db_manager
