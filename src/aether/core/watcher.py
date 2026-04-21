import time
import asyncio
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional, Callable, List

class ProjectWatcher(FileSystemEventHandler):
    def __init__(self, loop, on_modified_callback: Callable, required_exts: List[str]):
        self.loop = loop
        self.on_modified_callback = on_modified_callback
        self.required_exts = required_exts
        self.last_triggered = 0
        self.debounce_seconds = 5

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Extension Filter
        ext = Path(event.src_path).suffix.lower()
        if ext not in self.required_exts:
            return

        if any(x in event.src_path for x in [".git", "__pycache__", "storage", ".venv"]):
            return
        
        current_time = time.time()
        if current_time - self.last_triggered > self.debounce_seconds:
            self.last_triggered = current_time
            print(f"Auto-sync triggered by: {event.src_path}")
            # Use the provided callback
            asyncio.run_coroutine_threadsafe(self.on_modified_callback(), self.loop)

def setup_watcher(path: str, loop: asyncio.AbstractEventLoop, on_modified_callback: Callable, required_exts: List[str]) -> Optional[Observer]:
    """Helper to initialize and start a watchdog observer."""
    if not path or not os.path.exists(path):
        return None
        
    observer = Observer()
    handler = ProjectWatcher(loop, on_modified_callback, required_exts)
    observer.schedule(handler, path, recursive=True)
    observer.start()
    return observer
