#!/usr/bin/env python3
"""
Development server with hot reload functionality.
Watches for file changes and gracefully restarts the main server.
"""

import subprocess
import signal
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartHandler(FileSystemEventHandler):
    """Handler for file system events that triggers server restarts."""
    
    def __init__(self):
        self.process = None
        self.restart_server()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory or not str(event.src_path).endswith('.py'):
            return
        
        print(f'📝 File changed: {event.src_path}')
        self.restart_server()
    
    def restart_server(self):
        """Gracefully restart the server process."""
        if self.process:
            print('🔄 Gracefully shutting down server...')
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print('⚠️  Force killing server...')
                self.process.kill()
                self.process.wait()
        
        print('🚀 Starting server...')
        self.process = subprocess.Popen([
            'uv', 'run', 'python', 'main.py',
            '--primary-workers', '1',
            '--retry-workers', '0',
        ])
    
    def stop(self):
        """Stop the server process."""
        if self.process:
            print('🛑 Stopping server...')
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def main():
    """Main function to set up file watching and handle signals."""
    print("Starting development server with hot reload...")
    print("💡 File changes will trigger graceful restart")
    print("🔄 Watching: server/, tts/, worker/, *.py")
    print("⏹️  Press Ctrl+C to stop")
    
    handler = RestartHandler()
    observer = Observer()
    
    # Watch directories
    observer.schedule(handler, 'server', recursive=True)
    observer.schedule(handler, 'tts', recursive=True)
    observer.schedule(handler, 'worker', recursive=True)
    observer.schedule(handler, '.', recursive=False)
    
    observer.start()
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        print('\n🛑 Shutting down...')
        observer.stop()
        handler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == '__main__':
    main()
