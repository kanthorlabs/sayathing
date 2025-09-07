"""
Test to verify that the HTTP server and workers share the same DatabaseManager singleton.
"""

import pytest

from container import container, initialize_container
from server.config.app import create_app


@pytest.fixture
async def initialized_container():
    """Fixture to initialize the container before tests."""
    await initialize_container()
    yield container
    # Cleanup is handled by other fixtures if needed


class TestSharedDatabaseManager:
    """Test class for shared DatabaseManager functionality."""

    async def test_server_and_workers_share_database_manager(self, initialized_container):
        """Test that server and workers share the same DatabaseManager instance."""
        # This is what the workers would get
        worker_db_manager = container.database_manager()

        # This is what the server would get
        create_app()
        server_queue = container.worker_queue()
        server_db_manager = server_queue.db_manager

        # Verify they are the same instance
        assert (
            worker_db_manager is server_db_manager
        ), "Server and workers should share the same DatabaseManager instance"
        assert id(worker_db_manager) == id(server_db_manager), "DatabaseManager instances should be identical"

    async def test_multiple_worker_queues_share_database_manager(self, initialized_container):
        """Test that all worker queues share the same singleton DatabaseManager."""
        worker_db_manager = container.database_manager()
        worker_queue1 = container.worker_queue()
        worker_queue2 = container.worker_queue()

        assert worker_queue1.db_manager is worker_db_manager, "Worker queue 1 should use singleton DatabaseManager"
        assert worker_queue2.db_manager is worker_db_manager, "Worker queue 2 should use singleton DatabaseManager"
        assert worker_queue1.db_manager is worker_queue2.db_manager, "All worker queues should use same DatabaseManager"

    async def test_database_operations_work(self, initialized_container):
        """Test that database operations work with shared DatabaseManager."""
        worker_queue = container.worker_queue()

        # Test database operations work
        await worker_queue.initialize()

        # Verify database manager properties are accessible
        db_manager = worker_queue.db_manager
        assert hasattr(db_manager, "database_url"), "DatabaseManager should have database_url attribute"

        await worker_queue.close()
