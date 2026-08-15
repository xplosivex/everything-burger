# In-memory generation state (process-local, lost on restart).
generated_content = {}


def count_active_generations(user_id):
    return len([
        task_id for task_id, content in generated_content.items()
        if content['user_id'] == user_id and not content['completed']
    ])
