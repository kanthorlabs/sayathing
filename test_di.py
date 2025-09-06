#!/usr/bin/env python3
"""
Quick test to verify dependency injection is working correctly.
"""
import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from worker import container, create_test_container, QueueConfig, initialize_container


async def test_di_setup():
    """Test that dependency injection is working"""
    print("Testing dependency injection setup...")
    
    # Test 1: Initialize container
    print("1. Testing container initialization...")
    await initialize_container()
    print("   ✓ Container initialized successfully")
    
    # Test 2: Global container singleton behavior
    print("2. Testing global container...")
    global_queue1 = container.worker_queue()
    global_queue2 = container.worker_queue()
    global_db_manager1 = container.database_manager()
    global_db_manager2 = container.database_manager()
    
    # DatabaseManager should be singleton
    assert global_db_manager1 is global_db_manager2, "DatabaseManager should be singleton"
    print("   ✓ DatabaseManager is singleton in global container")
    
    # Both queues should use the same database manager
    assert global_queue1.db_manager is global_db_manager1, "Queue 1 should use singleton DatabaseManager"
    assert global_queue2.db_manager is global_db_manager1, "Queue 2 should use singleton DatabaseManager"
    assert global_queue1.db_manager is global_queue2.db_manager, "Both queues should use the same DatabaseManager"
    print("   ✓ All queues use the same singleton DatabaseManager")
    
    # Test 3: Test container with custom config
    print("3. Testing test container...")
    test_config = QueueConfig(database_url="sqlite+aiosqlite:///:memory:")
    test_container = create_test_container(test_config)
    
    test_queue = test_container.worker_queue()
    test_db_manager1 = test_container.database_manager()
    test_db_manager2 = test_container.database_manager()
    
    # DatabaseManager should be singleton within test container
    assert test_db_manager1 is test_db_manager2, "DatabaseManager should be singleton in test container"
    print("   ✓ DatabaseManager is singleton in test container")
    
    # Global and test containers should have different instances
    assert global_db_manager1 is not test_db_manager1, "Different containers should have different DatabaseManager instances"
    print("   ✓ Different containers have different DatabaseManager instances")
    
    # Test 4: Queue initialization
    print("4. Testing queue initialization...")
    await test_queue.initialize()
    print("   ✓ Queue initialization successful")
    
    # Test 5: Database manager is properly injected
    assert test_queue.db_manager is test_db_manager1, "Queue should use the injected DatabaseManager"
    print("   ✓ Queue uses injected DatabaseManager")
    
    await test_queue.close()
    
    print("\n✅ All dependency injection tests passed!")
    print("🔄 IMPORTANT: All components (HTTP server, primary workers, retry workers) will share the same DatabaseManager singleton")


if __name__ == "__main__":
    asyncio.run(test_di_setup())
