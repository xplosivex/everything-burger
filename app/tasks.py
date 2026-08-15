import json
import logging

from app.models import db, User, Page, PageIteration
from app.state import update
from app.generation.pipeline import generate_html_optimized
from app.generation.iterations import generate_iteration, generate_watcher_verdict
from app.routes.helpers import update_quest_progress, update_achievement_progress
from app.routes.generation import try_reward_item
from app.extensions import socketio

logger = logging.getLogger(__name__)


def run_generate(app, task_id, prompt, user_id):
    """Generate a page in the background and push the result to the client."""
    with app.app_context():
        try:
            result, archetype_key, meta = generate_html_optimized(prompt, user_id)
            if not result or len(result.strip()) < 100:
                update(task_id, error="Generation produced insufficient content", completed=True)
                return

            update(task_id, html=result, archetype=archetype_key, meta=meta, completed=True)
            socketio.emit('generation_complete', {
                'html': result,
                'prompt': prompt,
                'task_id': task_id,
                'status': 'success',
                'archetype': archetype_key,
                'meta': meta
            })
        except Exception as e:
            logger.error(f"Generation failed for task {task_id}: {e}")
            update(task_id, error=str(e), completed=True)
            socketio.emit('generation_complete', {
                'html': None,
                'prompt': prompt,
                'task_id': task_id,
                'status': 'error',
                'message': str(e)
            })


def run_iterate(app, task_id, page_uuid, parent_iteration_id, prompt, user_id):
    """Rewrite a page in the background and notify the client."""
    with app.app_context():
        try:
            page = Page.query.filter_by(uuid=page_uuid).first_or_404()
            parent_iteration = PageIteration.query.get_or_404(parent_iteration_id)

            # Re-run the archetype pipeline with the page's stored archetype,
            # seeding the content stage with the existing page text so the
            # modification is applied while the format is preserved.
            from bs4 import BeautifulSoup as _BS
            soup = _BS(parent_iteration.html_content, 'html.parser')
            for tag in soup(['script', 'style', 'head']):
                tag.decompose()
            seed_text = soup.get_text(separator='\n', strip=True)[:15000]

            html, _, meta = generate_html_optimized(
                prompt, user_id,
                archetype_key=page.archetype,
                seed_text=seed_text,
                award=False
            )
            iteration = PageIteration(
                page_id=page.id,
                parent_iteration_id=parent_iteration.id,
                html_content=html,
                prompt=prompt,
                author_id=user_id,
                iteration_number=parent_iteration.iteration_number + 1,
                meta_json=json.dumps(meta)
            )
            db.session.add(iteration)
            db.session.commit()

            iterator = User.query.get(user_id)
            iterator.xp += 25
            iterator.current_crumbs += 10
            iterator.lifetime_crumbs += 10

            if page.creator_id != user_id:
                owner = User.query.get(page.creator_id)
                if owner:
                    owner.xp += 10
                update_achievement_progress(page.creator_id, 'fork_in_the_road', 1)

            user_iteration_count = db.session.query(PageIteration).filter_by(author_id=user_id).count()
            update_achievement_progress(user_id, 'branching_out', user_iteration_count)
            update_quest_progress(user_id, 'iterate_pages')
            db.session.commit()

            try_reward_item(user_id, prompt)

            socketio.emit('iteration_complete', {
                'task_id': task_id,
                'iteration_id': iteration.id,
                'page_uuid': page_uuid
            })

        except Exception as e:
            logger.error(f"iterate error for task {task_id}: {e}")
            socketio.emit('iteration_error', {'task_id': task_id, 'error': str(e)})


def run_watcher_verdict(app, iteration_id):
    """Score a page iteration with the Watcher AI in the background."""
    with app.app_context():
        generate_watcher_verdict(iteration_id, app)
