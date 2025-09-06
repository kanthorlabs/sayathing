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
from ..task import Task, TaskItem, TaskState
from ..config import QueueConfig, WorkerConfig
from ..database import DatabaseManager
from tts.tts import TextToSpeechRequest

class RetryWorker:
    """
    Retry worker for processing retryable TTS tasks from the queue.
    
    This worker handles text-to-speech tasks that have failed previously by
    finding retryable tasks, moving them back to pending state, and processing
    them again with proper retry logic and exponential backoff.
    """
    
    def __init__(self, worker_id: str = f"retry-{time.time()}", queue: Optional[WorkerQueue] = None, database_manager: Optional[DatabaseManager] = None):
        self.worker_id = worker_id
        self.logger = logging.getLogger(f"worker-{self.worker_id}")
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self.queue = queue
        self.db_manager = database_manager
        
        # Get configuration from environment
        self.queue_config = QueueConfig.from_env()
        self.worker_config = WorkerConfig.from_env()
        self.poll_delay = self.worker_config.retry_worker_poll_delay
        self.batch_size = self.worker_config.retry_worker_batch_size
        self.visibility_timeout = self.worker_config.retry_worker_visibility_timeout
        self.max_attempts = self.worker_config.retry_worker_max_attempts
        
    async def startup(self):
        """Initialize the worker and dependencies"""
        self.logger.info(f"Starting retry worker {self.worker_id}")
        
        # If dependencies not provided, create them (fallback)
        if self.db_manager is None:
            self.db_manager = DatabaseManager(self.queue_config.database_url)
            await self.db_manager.initialize()
        
        if self.queue is None:
            self.queue = WorkerQueue(self.queue_config, self.db_manager)
            await self.queue.initialize()
        
        self.is_running = True
        self.logger.info(f"Retry worker {self.worker_id} started successfully")
        
    async def shutdown(self):
        """Clean shutdown of the worker"""
        self.logger.info(f"Shutting down retry worker {self.worker_id}")
        self.is_running = False
        self._shutdown_event.set()
        
        if self.queue:
            await self.queue.close()
            
        if self.db_manager:
            await self.db_manager.close()
            
        self.logger.info(f"Retry worker {self.worker_id} shutdown complete")
        
    async def run(self):
        """
        Main retry worker loop following Python async best practices.
        
        Continuously polls for retryable tasks, processes retry logic, and then
        processes the tasks that are moved back to pending until shutdown is requested.
        """
        if not self.is_running:
            await self.startup()
            
        self.logger.info(f"Retry worker {self.worker_id} entering main loop")
        
        try:
            while self.is_running:
                try:
                    # Check for shutdown signal
                    if self._shutdown_event.is_set():
                        break
                        
                    # Process retryable tasks - this moves retryable tasks back to pending
                    # or discards them if they've exceeded max attempts
                    retry_tasks = await self.queue.retry(
                        size=self.batch_size,
                        visibility_timeout=self.visibility_timeout,
                        max_attempts=self.max_attempts
                    )
                    
                    if retry_tasks:
                        self.logger.info(f"Processed {len(retry_tasks)} tasks for retry")
                        
                        # Filter tasks that are now pending (not discarded) and ready to process
                        pending_tasks = [
                            task for task in retry_tasks 
                            if task.state == TaskState.PENDING and task.schedule_at <= int(time.time() * 1000)
                        ]
                        
                        if pending_tasks:
                            # Process the newly pending tasks
                            await self._process_tasks_batch(pending_tasks)
                    
                    # If no retryable tasks found, wait before polling again
                    if not retry_tasks:
                        self.logger.debug(f"No retryable tasks available, waiting {self.poll_delay}s before next poll")
                        try:
                            await asyncio.wait_for(
                                self._shutdown_event.wait(), 
                                timeout=self.poll_delay
                            )
                            break  # Shutdown was signaled
                        except asyncio.TimeoutError:
                            continue  # Timeout reached, continue polling
                    
                except Exception as e:
                    self.logger.error(f"Retry worker {self.worker_id} loop error: {e}", exc_info=True)
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
            self.logger.error(f"Fatal error in retry worker {self.worker_id}: {e}", exc_info=True)
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
            # First, we need to claim the task by moving it to PROCESSING state
            # since the retry() method only moves it to PENDING
            await self._claim_task_for_processing(task.id)
            
            success = await self.process_task(task)
            if success:
                await self.queue.mark_as_complete(task)
                self.logger.info(f"Completed retry task {task.id} after {task.attempt_count} attempts")
            else:
                await self.queue.mark_as_retry(task.id, "Retry processing failed")
                self.logger.warning(f"Retrying task {task.id} again after failed retry attempt")
                
        except Exception as e:
            error_msg = f"Error processing retry task {task.id}: {str(e)}"
            try:
                await self.queue.mark_as_retry(task.id, error_msg)
            except Exception as mark_error:
                self.logger.error(f"Failed to mark task {task.id} as retry: {mark_error}")
            self.logger.error(error_msg, exc_info=True)
            
    async def _claim_task_for_processing(self, task_id: str):
        """
        Claim a pending task for processing by moving it to PROCESSING state.
        This is necessary because retry() moves tasks to PENDING, but we need
        them in PROCESSING state to mark them as complete or retry.
        """
        try:
            # Use the queue's internal update method to transition from PENDING to PROCESSING
            await self.queue._update_task_state(
                task_id, 
                TaskState.PROCESSING, 
                expected_state=TaskState.PENDING
            )
        except Exception as e:
            self.logger.error(f"Failed to claim task {task_id} for processing: {e}")
            raise
            
    async def process_task(self, task: Task) -> bool:
        """
        Process a TTS task using the TTS module.
        
        Args:
            task: The task to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing retry task {task.id} (attempt {task.attempt_count})")
            
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
                    
                    self.logger.debug(f"Generated audio for retry task {task.id}, size: {len(tts_response.audio)} bytes")
                    
                except Exception as e:
                    error_msg = f"Failed to process task item in retry task {task.id}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    raise
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process retry task {task.id}: {str(e)}", exc_info=True)
            return False


async def main():
    """Main entry point for the retry worker when run as a script"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create retry worker instance
    worker = RetryWorker()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(worker.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Run the retry worker
        await worker.run()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Retry worker failed with error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("Retry worker shutdown complete")


if __name__ == "__main__":
    # Entry point for running as a script or in a Docker container
    asyncio.run(main())
    asyncio.run(main())
