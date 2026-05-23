import time
import asyncio
import os
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional, Callable, List

logger = logging.getLogger("aether.watcher")

class ProjectWatcher(FileSystemEventHandler):
    def __init__(self, loop, on_modified_callback: Callable, required_exts: List[str], auto_sync: bool = False, on_change_detected_callback: Optional[Callable] = None):
        self.loop = loop
        self.on_modified_callback = on_modified_callback
        self.required_exts = required_exts
        self.auto_sync = auto_sync
        self.on_change_detected_callback = on_change_detected_callback
        self.last_triggered = 0
        self.debounce_seconds = 5

    def on_modified(self, event):
        self._handle_event(event)

    def on_created(self, event):
        self._handle_event(event)

    def on_deleted(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        if event.is_directory:
            return
        
        # Extension Filter
        ext = Path(event.src_path).suffix.lower()
        if ext not in self.required_exts:
            return

        # Path exclusion filter
        if any(x in event.src_path for x in [".git", "__pycache__", "storage", ".venv", ".ruff_cache", ".pytest_cache", ".mypy_cache"]):
            return
        
        current_time = time.time()
        if current_time - self.last_triggered > self.debounce_seconds:
            self.last_triggered = current_time
            logger.info(f"Change detected by watcher: {event.event_type} on {event.src_path}")
            if self.auto_sync:
                # Use the provided callback
                asyncio.run_coroutine_threadsafe(self.on_modified_callback(), self.loop)
            else:
                if self.on_change_detected_callback:
                    self.loop.call_soon_threadsafe(self.on_change_detected_callback)

def setup_watcher(
    path: str,
    loop: asyncio.AbstractEventLoop,
    on_modified_callback: Callable,
    required_exts: List[str],
    auto_sync: bool = False,
    on_change_detected_callback: Optional[Callable] = None
) -> Optional[Observer]:
    """Helper to initialize and start a watchdog observer."""
    if not path or not os.path.exists(path):
        return None
        
    observer = Observer()
    handler = ProjectWatcher(
        loop=loop,
        on_modified_callback=on_modified_callback,
        required_exts=required_exts,
        auto_sync=auto_sync,
        on_change_detected_callback=on_change_detected_callback
    )
    observer.schedule(handler, path, recursive=True)
    observer.start()
    return observer

if __name__ == "__main__":
    import unittest
    from unittest.mock import MagicMock

    class TestProjectWatcher(unittest.TestCase):
        def test_handle_event_detect_only(self):
            # Set up mock event
            mock_event = MagicMock()
            mock_event.is_directory = False
            mock_event.src_path = "test_file.py"
            mock_event.event_type = "modified"

            # Set up mock loop and callback
            mock_loop = MagicMock()
            callback_called = False
            
            def mock_callback():
                nonlocal callback_called
                callback_called = True

            # Instantiate ProjectWatcher with auto_sync=False
            watcher = ProjectWatcher(
                loop=mock_loop,
                on_modified_callback=MagicMock(),
                required_exts=[".py"],
                auto_sync=False,
                on_change_detected_callback=mock_callback
            )

            # Trigger handle_event
            watcher._handle_event(mock_event)

            # Verify that call_soon_threadsafe was called with mock_callback
            mock_loop.call_soon_threadsafe.assert_called_once_with(mock_callback)

    print("Running ProjectWatcher unit tests...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProjectWatcher)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
