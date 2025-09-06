#!/usr/bin/env python3
"""
SayAThing CLI - Text-to-Speech Service Management

This script provides a unified CLI for managing the SayAThing TTS service,
including the HTTP server and worker processes.
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from typing import List, Optional
import multiprocessing

import uvicorn

from server.http import app
from worker.workers.primary_worker import PrimaryWorker
from worker.workers.retry_worker import RetryWorker


class ServiceManager:
    """Manages the lifecycle of HTTP server and worker processes"""
    
    def __init__(self, enable_http: bool = True, primary_workers: int = 1, retry_workers: int = 1):
        self.enable_http = enable_http
        self.primary_workers = max(0, primary_workers)
        self.retry_workers = max(0, retry_workers)
        
        self.logger = logging.getLogger("service-manager")
        self.shutdown_event = asyncio.Event()
        self.tasks: List[asyncio.Task] = []
        
        # Signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self._trigger_shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _trigger_shutdown(self):
        """Trigger shutdown event"""
        self.shutdown_event.set()
    
    async def _run_http_server(self):
        """Run the HTTP server"""
        self.logger.info("Starting HTTP server...")
        
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        # Create a task for the server
        server_task = asyncio.create_task(server.serve())
        
        try:
            # Wait for either server completion or shutdown signal
            await asyncio.wait(
                [server_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            if not server_task.done():
                self.logger.info("Shutting down HTTP server...")
                server.should_exit = True
                await server_task
    
    async def _run_primary_worker(self, worker_id: str):
        """Run a primary worker"""
        self.logger.info(f"Starting primary worker {worker_id}")
        
        worker = PrimaryWorker(worker_id=worker_id)
        
        try:
            # Start the worker
            worker_task = asyncio.create_task(worker.run())
            
            # Wait for either worker completion or shutdown signal
            await asyncio.wait(
                [worker_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            if worker.is_running:
                self.logger.info(f"Shutting down primary worker {worker_id}")
                await worker.shutdown()
    
    async def _run_retry_worker(self, worker_id: str):
        """Run a retry worker"""
        self.logger.info(f"Starting retry worker {worker_id}")
        
        worker = RetryWorker(worker_id=worker_id)
        
        try:
            # Start the worker
            worker_task = asyncio.create_task(worker.run())
            
            # Wait for either worker completion or shutdown signal
            await asyncio.wait(
                [worker_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            if worker.is_running:
                self.logger.info(f"Shutting down retry worker {worker_id}")
                await worker.shutdown()
    
    async def run(self):
        """Run all configured services"""
        self.logger.info(f"Starting SayAThing service manager...")
        self.logger.info(f"Configuration: HTTP={self.enable_http}, Primary Workers={self.primary_workers}, Retry Workers={self.retry_workers}")
        
        try:
            # Create tasks for all services
            if self.enable_http:
                self.tasks.append(asyncio.create_task(self._run_http_server()))
            
            # Create primary worker tasks
            for i in range(self.primary_workers):
                worker_id = f"primary-{i}-{int(time.time())}"
                self.tasks.append(asyncio.create_task(self._run_primary_worker(worker_id)))
            
            # Create retry worker tasks
            for i in range(self.retry_workers):
                worker_id = f"retry-{i}-{int(time.time())}"
                self.tasks.append(asyncio.create_task(self._run_retry_worker(worker_id)))
            
            if not self.tasks:
                self.logger.warning("No services configured to run. Exiting.")
                return
            
            # Wait for all tasks to complete or shutdown signal
            self.logger.info(f"All services started. Running {len(self.tasks)} tasks...")
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Service manager error: {e}", exc_info=True)
            raise
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Clean up resources and cancel tasks"""
        self.logger.info("Performing cleanup...")
        
        # Cancel all remaining tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to be cancelled
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.logger.info("Cleanup complete")


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser"""
    parser = argparse.ArgumentParser(
        description="SayAThing - Text-to-Speech Service Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run HTTP server only
  python main.py --no-workers
  
  # Run workers only (no HTTP server)
  python main.py --no-http --primary-workers 2 --retry-workers 1
  
  # Run full service with custom worker counts
  python main.py --primary-workers 4 --retry-workers 2
  
  # Run with minimal configuration
  python main.py --primary-workers 0 --retry-workers 0
        """
    )
    
    # HTTP server configuration
    parser.add_argument(
        "--no-http",
        action="store_true",
        help="Disable HTTP server (default: enabled)"
    )
    
    # Worker configuration
    parser.add_argument(
        "--primary-workers",
        type=int,
        default=1,
        help="Number of primary workers to spawn (default: 1, minimum: 0)"
    )
    
    parser.add_argument(
        "--retry-workers",
        type=int,
        default=1,
        help="Number of retry workers to spawn (default: 1, minimum: 0)"
    )
    
    parser.add_argument(
        "--no-workers",
        action="store_true",
        help="Disable all workers (equivalent to --primary-workers 0 --retry-workers 0)"
    )
    
    # Logging configuration
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    return parser


async def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger("main")
    
    # Determine service configuration
    enable_http = not args.no_http
    
    if args.no_workers:
        primary_workers = 0
        retry_workers = 0
    else:
        primary_workers = max(0, args.primary_workers)
        retry_workers = max(0, args.retry_workers)
    
    # Validate configuration
    if not enable_http and primary_workers == 0 and retry_workers == 0:
        logger.error("No services configured to run. Enable at least one service.")
        sys.exit(1)
    
    # Create and run service manager
    service_manager = ServiceManager(
        enable_http=enable_http,
        primary_workers=primary_workers,
        retry_workers=retry_workers
    )
    
    try:
        await service_manager.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Service manager shutdown complete")


if __name__ == "__main__":
    # Check if we're running in Python 3.12+
    if sys.version_info < (3, 12):
        print("ERROR: This application requires Python 3.12 or higher", file=sys.stderr)
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGracefully shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
