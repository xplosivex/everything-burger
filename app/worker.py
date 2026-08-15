import logging
import threading

from app.queue import dequeue
from app import tasks

logger = logging.getLogger(__name__)

# Dispatch table: task type -> handler(app, **payload)
DISPATCH = {
    'generate': tasks.run_generate,
    'iterate': tasks.run_iterate,
    'watcher_verdict': tasks.run_watcher_verdict,
}


def _worker_loop(app, stop_event):
    """Consume jobs from the Redis queue until stop_event is set."""
    logger.info("Queue worker started")
    while not stop_event.is_set():
        try:
            job = dequeue(timeout=1)
            if job is None:
                continue
            task_type, payload = job
            handler = DISPATCH.get(task_type)
            if handler is None:
                logger.error(f"Unknown task type: {task_type}")
                continue
            logger.info(f"Processing {task_type} task {payload.get('task_id', '')}")
            handler(app, **payload)
        except Exception as e:
            logger.error(f"Queue worker error: {e}")
    logger.info("Queue worker stopped")


def start_workers(app, count):
    """Start `count` embedded worker threads in this process."""
    stop_event = threading.Event()
    workers = []
    for i in range(count):
        t = threading.Thread(
            target=_worker_loop,
            args=(app, stop_event),
            daemon=True,
            name=f'qw-{i}',
        )
        t.start()
        workers.append(t)
    logger.info(f"Started {count} queue workers")
    return stop_event, workers
