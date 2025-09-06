import asyncio
import logging
import signal
import sys
import os
import base64
import json
import time
from typing import Optional, List

from ..queue import WorkerQueue
from ..task import Task, TaskItem
from ..config import QueueConfig, WorkerConfig
from ..database import DatabaseManager
from tts.tts import TextToSpeechRequest

class PrimaryWorker:
    """
    Primary worker for processing TTS tasks from the queue.
    
    This worker handles text-to-speech tasks by dequeuing them from the queue,
    processing them using the TTS engine, and updating the task status.
    """
    
    def __init__(self, worker_id: str = str(time.time())):
        self.worker_id = worker_id
        self.logger = logging.getLogger(f"worker-{self.worker_id}")
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self.queue: Optional[WorkerQueue] = None
        self.db_manager: Optional[DatabaseManager] = None
        
        # Configuration from environment variables
        self.queue_config = QueueConfig.from_env()
        self.worker_config = WorkerConfig.from_env()
        self.poll_delay = self.worker_config.worker_poll_delay
        self.batch_size = self.worker_config.worker_batch_size
        
    async def startup(self):
        """Initialize the worker and dependencies"""
        self.logger.info(f"Starting worker {self.worker_id}")
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.queue_config.database_url)
        await self.db_manager.initialize()
        
        # Initialize queue
        self.queue = WorkerQueue(self.queue_config)
        
        self.is_running = True
        self.logger.info(f"Worker {self.worker_id} started successfully")
        
    async def shutdown(self):
        """Clean shutdown of the worker"""
        self.logger.info(f"Shutting down worker {self.worker_id}")
        self.is_running = False
        self._shutdown_event.set()
        
        if self.db_manager:
            await self.db_manager.close()
            
        self.logger.info(f"Worker {self.worker_id} shutdown complete")
        
    async def run(self):
        """
        Main worker loop following Python async best practices.
        
        Continuously polls for tasks and processes them until shutdown is requested.
        """
        if not self.is_running:
            await self.startup()
            
        self.logger.info(f"Worker {self.worker_id} entering main loop")
        
        try:
            while self.is_running:
                try:
                    # Check for shutdown signal
                    if self._shutdown_event.is_set():
                        break
                        
                    # Dequeue tasks
                    tasks = await self.queue.dequeue(size=self.batch_size)
                    
                    if not tasks:
                        # No tasks available, wait before polling again
                        self.logger.debug(f"No tasks available, waiting {self.poll_delay}s before next poll")
                        try:
                            await asyncio.wait_for(
                                self._shutdown_event.wait(), 
                                timeout=self.poll_delay
                            )
                            break  # Shutdown was signaled
                        except asyncio.TimeoutError:
                            continue  # Timeout reached, continue polling
                    
                    # Process tasks concurrently
                    await self._process_tasks_batch(tasks)
                    
                except Exception as e:
                    self.logger.error(f"Worker {self.worker_id} loop error: {e}", exc_info=True)
                    # Back off on errors to avoid tight error loops
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), 
                            timeout=5
                        )
                        break  # Shutdown was signaled
                    except asyncio.TimeoutError:
                        continue  # Continue after backoff
                        
        except Exception as e:
            self.logger.error(f"Fatal error in worker {self.worker_id}: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
            
    async def _process_tasks_batch(self, tasks: List[Task]):
        """Process a batch of tasks concurrently"""
        # Create coroutines for all tasks
        task_coroutines = [self._process_single_task(task) for task in tasks]
        
        # Process all tasks concurrently
        await asyncio.gather(*task_coroutines, return_exceptions=True)
        
    async def _process_single_task(self, task: Task):
        """Process a single task with proper error handling"""
        try:
            success = await self.process_task(task)
            if success:
                await self.queue.mark_as_complete(task.id)
                self.logger.info(f"Completed task {task.id}")
            else:
                await self.queue.mark_as_retry(task.id, "Processing failed")
                self.logger.warning(f"Retrying task {task.id}")
                
        except Exception as e:
            error_msg = f"Error processing task {task.id}: {str(e)}"
            await self.queue.mark_as_retry(task.id, error_msg)
            self.logger.error(error_msg, exc_info=True)
            
    async def process_task(self, task: Task) -> bool:
        """
        Process a TTS task using the TTS module.
        
        Args:
            task: The task to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing task {task.id}")
            
            # Process each task item
            for item in task.items:
                try:
                    # Parse the TTS request from the task item
                    if isinstance(item.request, dict):
                        tts_request = TextToSpeechRequest(**item.request)
                    elif isinstance(item.request, str):
                        tts_request = TextToSpeechRequest.from_json(item.request)
                    else:
                        tts_request = item.request
                        
                    # Execute TTS processing
                    tts_response = await tts_request.execute_async()
                    
                    # Use the audio_base64 property and update response_url
                    item.response_url = f"data:audio/wav;base64,{tts_response.audio_base64}"
                    
                    self.logger.debug(f"Generated audio for task {task.id}, size: {len(tts_response.audio)} bytes")
                    
                except Exception as e:
                    error_msg = f"Failed to process task item in {task.id}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    raise
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process task {task.id}: {str(e)}", exc_info=True)
            return False


async def main():
    """Main entry point for the worker when run as a script"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create worker instance
    worker = PrimaryWorker()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(worker.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Run the worker
        await worker.run()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Worker failed with error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("Worker shutdown complete")


if __name__ == "__main__":
    # Entry point for running as a script or in a Docker container
    asyncio.run(main())