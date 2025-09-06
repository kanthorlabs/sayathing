#!/usr/bin/env python3
"""
Test to verify that the HTTP server and workers share the same DatabaseManager singleton.
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from worker import container, initialize_container
from server.config.app import create_app


async def test_shared_database_manager():
    """Test that server and workers share the same DatabaseManager instance"""
    print("Testing shared DatabaseManager between server and workers...")
    
    # Initialize the container
    print("1. Initializing DI container...")
    await initialize_container()
    print("   ✓ Container initialized")
    
    # Get DatabaseManager instances that would be used by different components
    print("2. Getting DatabaseManager instances...")
    
    # This is what the workers would get
    worker_db_manager = container.database_manager()
    
    # This is what the server would get
    app = create_app()
    server_queue = container.worker_queue()
    server_db_manager = server_queue.db_manager
    
    # Verify they are the same instance
    print("3. Verifying singleton behavior...")
    assert worker_db_manager is server_db_manager, "Server and workers should share the same DatabaseManager instance"
    print(f"   ✓ DatabaseManager instances are identical: {id(worker_db_manager) == id(server_db_manager)}")
    
    # Get multiple worker instances to verify they all share the same DB manager
    worker_queue1 = container.worker_queue()
    worker_queue2 = container.worker_queue()
    
    assert worker_queue1.db_manager is worker_db_manager, "Worker queue 1 should use singleton DatabaseManager"
    assert worker_queue2.db_manager is worker_db_manager, "Worker queue 2 should use singleton DatabaseManager"
    print("   ✓ All worker queues use the same singleton DatabaseManager")
    
    print(f"\n✅ SUCCESS: All components share the same DatabaseManager singleton!")
    print(f"   DatabaseManager instance ID: {id(worker_db_manager)}")
    print(f"   Database URL: {worker_db_manager.database_url}")
    
    # Test database operations work
    print("\n4. Testing database operations...")
    await worker_queue1.initialize()
    print("   ✓ Database operations successful")
    
    await worker_queue1.close()


if __name__ == "__main__":
    asyncio.run(test_shared_database_manager())
