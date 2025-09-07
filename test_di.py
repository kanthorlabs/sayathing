"""
Quick test to verify dependency injection is working correctly.
"""

import pytest

from container import container, create_test_container, initialize_container
from worker import QueueConfig


@pytest.fixture
async def initialized_container():
    """Fixture to initialize the container before tests."""
    await initialize_container()
    yield container
    # Cleanup is handled by other fixtures if needed


class TestDependencyInjection:
    """Test class for dependency injection functionality."""

    async def test_container_initialization(self, initialized_container):
        """Test that dependency injection container initializes correctly."""
        # Container should be initialized by the fixture
        assert initialized_container is not None

    async def test_global_container_singleton_behavior(self, initialized_container):
        """Test that DatabaseManager is singleton in global container."""
        global_queue1 = container.worker_queue()
        global_queue2 = container.worker_queue()
        global_db_manager1 = container.database_manager()
        global_db_manager2 = container.database_manager()

        # DatabaseManager should be singleton
        assert global_db_manager1 is global_db_manager2, "DatabaseManager should be singleton"

        # Both queues should use the same database manager
        assert global_queue1.db_manager is global_db_manager1, "Queue 1 should use singleton DatabaseManager"
        assert global_queue2.db_manager is global_db_manager1, "Queue 2 should use singleton DatabaseManager"
        assert global_queue1.db_manager is global_queue2.db_manager, "Both queues should use the same DatabaseManager"

    async def test_test_container_singleton_behavior(self):
        """Test that DatabaseManager is singleton within test container."""
        test_config = QueueConfig(database_url="sqlite+aiosqlite:///:memory:")
        test_container = create_test_container(test_config)

        test_db_manager1 = test_container.database_manager()
        test_db_manager2 = test_container.database_manager()

        # DatabaseManager should be singleton within test container
        assert test_db_manager1 is test_db_manager2, "DatabaseManager should be singleton in test container"

    async def test_different_containers_have_different_instances(self, initialized_container):
        """Test that global and test containers have different DatabaseManager instances."""
        global_db_manager = container.database_manager()

        test_config = QueueConfig(database_url="sqlite+aiosqlite:///:memory:")
        test_container = create_test_container(test_config)
        test_db_manager = test_container.database_manager()

        # Global and test containers should have different instances
        assert (
            global_db_manager is not test_db_manager
        ), "Different containers should have different DatabaseManager instances"

    async def test_queue_initialization_and_injection(self):
        """Test that queue initializes and uses injected DatabaseManager correctly."""
        test_config = QueueConfig(database_url="sqlite+aiosqlite:///:memory:")
        test_container = create_test_container(test_config)

        test_queue = test_container.worker_queue()
        test_db_manager = test_container.database_manager()

        # Queue initialization
        await test_queue.initialize()

        # Database manager is properly injected
        assert test_queue.db_manager is test_db_manager, "Queue should use the injected DatabaseManager"

        await test_queue.close()
