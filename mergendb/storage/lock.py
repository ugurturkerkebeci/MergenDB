import os
import time
import threading
from contextlib import contextmanager
from typing import Dict

class RWLock:
    """
    Re-entrant, fair Reader-Writer Lock for high-concurrency access
    to MergenDB table files. Allows multiple concurrent readers or
    a single exclusive writer with zero external dependencies.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)
        self._readers = 0
        self._writers = 0
        self._writing = False

    @contextmanager
    def read(self):
        with self._lock:
            while self._writing or self._writers > 0:
                self._read_ready.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._lock:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notify_all()

    @contextmanager
    def write(self):
        with self._lock:
            self._writers += 1
            while self._writing or self._readers > 0:
                self._read_ready.wait()
            self._writers -= 1
            self._writing = True
        try:
            yield
        finally:
            with self._lock:
                self._writing = False
                self._read_ready.notify_all()


class TableLockManager:
    """
    Global thread-safe registry mapping canonical filepaths to table RWLocks.
    Ensures per-table isolation: Table A queries never block Table B queries.
    """
    _locks: Dict[str, RWLock] = {}
    _meta_lock = threading.Lock()

    @classmethod
    def get_lock(cls, table_path: str) -> RWLock:
        norm_path = os.path.normcase(os.path.abspath(table_path))
        with cls._meta_lock:
            if norm_path not in cls._locks:
                cls._locks[norm_path] = RWLock()
            return cls._locks[norm_path]

    @classmethod
    def clear(cls):
        with cls._meta_lock:
            cls._locks.clear()


def safe_atomic_replace(source_path: str, target_path: str, max_retries: int = 15, delay: float = 0.05):
    """
    Atomically replaces target_path with source_path.
    On Windows, active readers or transient handles can briefly hold a file;
    this helper applies exponential backoff retries to guarantee safe atomic swaps.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            os.replace(source_path, target_path)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(delay * (1.2 ** attempt))

    if os.path.exists(source_path):
        raise OSError(f"Failed to atomically replace '{target_path}' with '{source_path}' after {max_retries} retries: {last_err}")
