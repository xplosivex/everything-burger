import threading

# In-memory generation state (process-local, lost on restart).
# A lock guards concurrent access from multiple waitress threads.
_generated_content = {}
_lock = threading.Lock()


def put(task_id, content):
    with _lock:
        _generated_content[task_id] = content


def get(task_id):
    with _lock:
        return _generated_content.get(task_id)


def get_all():
    with _lock:
        return dict(_generated_content)


def update(task_id, **kwargs):
    with _lock:
        if task_id in _generated_content:
            _generated_content[task_id].update(kwargs)


def contains(task_id):
    with _lock:
        return task_id in _generated_content


def count_active_generations(user_id):
    with _lock:
        return len([
            task_id for task_id, content in _generated_content.items()
            if content['user_id'] == user_id and not content['completed']
        ])
