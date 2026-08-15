import logging
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# A bounded thread pool used for background work (page generation, watcher
# verdicts, iteration rewrites). Using a pool (rather than spawning an
# unbounded thread per request) prevents the server from being overwhelmed
# when many users generate pages at the same time.
_executor = None
_executor_lock = threading.Lock()


def init_thread_pool(max_workers):
    """Create (or resize) the shared background thread pool."""
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False)
        _executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix='bg',
        )
        logger.info(f"Background thread pool initialized with {max_workers} workers")


def submit(fn, *args, **kwargs):
    """Submit a background task to the pool, returning a Future."""
    if _executor is None:
        raise RuntimeError("Thread pool not initialized. Call init_thread_pool first.")
    return _executor.submit(fn, *args, **kwargs)


def shutdown():
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False)
            _executor = None
