import json
import logging
import threading

import redis

from app.config import REDIS_URL

logger = logging.getLogger(__name__)

# A single shared Redis client for the whole process. redis-py pools its
# connections internally, so sharing one client across waitress threads is safe.
_client = None
_client_lock = threading.Lock()


def get_redis() -> redis.Redis:
    """Return the process-wide Redis client (created on first use)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = redis.Redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                )
                _client.ping()  # fail fast if Redis is unreachable
                logger.info("Connected to Redis at %s", REDIS_URL)
    return _client


# ---------------------------------------------------------------------------
# Task queue (a simple Redis list).
#
# Web processes push jobs onto the list; worker threads in the same process
# (or a separate process) pop them with a blocking BLPOP. Jobs are plain
# JSON payloads: {"task": <task_type>, "payload": {...}}.
# ---------------------------------------------------------------------------

_QUEUE_KEY = 'eb2:tasks'


def enqueue(task_type, payload):
    """Push a job onto the Redis task queue."""
    get_redis().rpush(_QUEUE_KEY, json.dumps({'task': task_type, 'payload': payload}))
    logger.info(f"Enqueued {task_type} task")


def dequeue(timeout=5):
    """Blocking pop from the task queue. Returns (task_type, payload) or None."""
    result = get_redis().blpop(_QUEUE_KEY, timeout=timeout)
    if not result:
        return None
    data = json.loads(result[1])
    return data['task'], data['payload']


def queue_size():
    return get_redis().llen(_QUEUE_KEY)
