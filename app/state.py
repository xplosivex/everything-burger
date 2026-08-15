import json
import logging
import time

from app.queue import get_redis

logger = logging.getLogger(__name__)

# Task state lives in Redis so it survives web-process restarts and is
# visible to every process (web + workers). Each task is a hash:
#
#   task:<task_id> -> { html, prompt, completed, error, user_id, created_at }
#
# Active (in-flight) generations are tracked in a per-user set so the
# "3 active generations" cap can be enforced cheaply:
#
#   eb2:active:<user_id> -> set of task_ids
#
# Old tasks expire after TASK_TTL so Redis doesn't grow forever.

_TASK_PREFIX = 'eb2:task:'
_ACTIVE_PREFIX = 'eb2:active:'
TASK_TTL = 60 * 60 * 24  # 24 hours

_CREATED_AT = 'created_at'


def _task_key(task_id):
    return f"{_TASK_PREFIX}{task_id}"


def _active_key(user_id):
    return f"{_ACTIVE_PREFIX}{user_id}"


def put(task_id, content):
    r = get_redis()
    data = dict(content)
    data.setdefault(_CREATED_AT, time.time())
    data['completed'] = '1' if data.get('completed') else '0'
    data = {k: ('' if v is None else str(v)) for k, v in data.items()}
    r.hset(_task_key(task_id), mapping=data)
    r.expire(_task_key(task_id), TASK_TTL)
    r.sadd(_active_key(data['user_id']), task_id)
    r.expire(_active_key(data['user_id']), TASK_TTL)


def get(task_id):
    r = get_redis()
    raw = r.hgetall(_task_key(task_id))
    if not raw:
        return None
    return _decode(raw)


def update(task_id, **kwargs):
    r = get_redis()
    key = _task_key(task_id)
    if not r.exists(key):
        return
    mapping = {}
    for k, v in kwargs.items():
        if v is None:
            mapping[k] = ''
        elif isinstance(v, bool):
            mapping[k] = '1' if v else '0'
        elif isinstance(v, (dict, list)):
            mapping[k] = json.dumps(v)
        else:
            mapping[k] = str(v)
    r.hset(key, mapping=mapping)
    if mapping.get('completed') == '1':
        _clear_active(task_id)


def contains(task_id):
    return get_redis().exists(_task_key(task_id)) == 1


def get_all():
    r = get_redis()
    keys = r.keys(f"{_TASK_PREFIX}*")
    tasks = {}
    for key in keys:
        task_id = key[len(_TASK_PREFIX):]
        raw = r.hgetall(key)
        if raw:
            tasks[task_id] = _decode(raw)
    return tasks


def count_active_generations(user_id):
    r = get_redis()
    active = r.smembers(_active_key(user_id))
    count = 0
    for task_id in active:
        key = _task_key(task_id)
        if r.exists(key) and r.hget(key, 'completed') == '0':
            count += 1
    return count


def _clear_active(task_id):
    r = get_redis()
    raw = r.hgetall(_task_key(task_id))
    if raw and 'user_id' in raw:
        r.srem(_active_key(raw['user_id']), task_id)


def _decode(raw):
    out = dict(raw)
    for k, v in out.items():
        if k == 'completed':
            out[k] = str(v) in ('1', 'True', 'true')
        elif k == 'user_id':
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = v
        elif k == 'meta':
            try:
                out[k] = json.loads(v)
            except (TypeError, ValueError):
                out[k] = None
        elif v == '':
            out[k] = None
    return out
