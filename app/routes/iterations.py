import uuid
import logging
from flask import Blueprint, render_template, request, url_for, session, jsonify
from app.extensions import socketio
from app.models import db, User, Page, PageIteration, WatcherVerdict
from app.utils import login_required
from app.generation.iterations import generate_iteration, generate_watcher_verdict
from app.generation.pipeline import get_prompt_length
from app.routes.helpers import update_quest_progress, update_achievement_progress
from app.routes.generation import try_reward_item
import gevent

logger = logging.getLogger(__name__)

iterations_bp = Blueprint('iterations', __name__)

@iterations_bp.route('/iterate/<page_uuid>', methods=['POST'])
@login_required
def iterate_page(page_uuid):
    page = Page.query.filter_by(uuid=page_uuid).first_or_404()

    if page.visibility == 'private' and page.creator_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403

    modification_prompt = request.form.get('prompt', '').strip()
    parent_iteration_id = request.form.get('parent_iteration_id') or page.current_iteration_id

    prompt_limit = get_prompt_length(session['user_id'])
    if not modification_prompt:
        return jsonify({'error': 'Prompt required'}), 400
    if len(modification_prompt) > prompt_limit:
        return jsonify({'error': f'Prompt too long ({len(modification_prompt)}/{prompt_limit} chars)'}), 400
    if not parent_iteration_id:
        return jsonify({'error': 'No parent iteration found'}), 400

    try:
        parent_iteration_id = int(parent_iteration_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid parent iteration'}), 400

    parent_iteration = PageIteration.query.get_or_404(parent_iteration_id)
    task_id = str(uuid.uuid4())
    user_id = session['user_id']

    def iterate_async():
        with app.app_context():
            try:
                html = generate_iteration(
                    parent_html=parent_iteration.html_content,
                    modification_prompt=modification_prompt,
                    original_prompt=page.prompt
                )
                iteration = PageIteration(
                    page_id=page.id,
                    parent_iteration_id=parent_iteration.id,
                    html_content=html,
                    prompt=modification_prompt,
                    author_id=user_id,
                    iteration_number=parent_iteration.iteration_number + 1
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

                try_reward_item(user_id, modification_prompt)
                gevent.spawn(generate_watcher_verdict, iteration.id)

                socketio.emit('iteration_complete', {
                    'task_id': task_id,
                    'iteration_id': iteration.id,
                    'page_uuid': page_uuid
                })

            except Exception as e:
                logger.error(f"iterate_async error: {e}")
                socketio.emit('iteration_error', {'task_id': task_id, 'error': str(e)})

    gevent.spawn(iterate_async)
    return jsonify({'task_id': task_id, 'redirect': url_for('iterations.iteration_loading', task_id=task_id, page_uuid=page_uuid)})


@iterations_bp.route('/iteration_loading/<task_id>/<page_uuid>')
@login_required
def iteration_loading(task_id, page_uuid):
    page = Page.query.filter_by(uuid=page_uuid).first_or_404()
    user = User.query.get(session['user_id'])
    crumb_balance = user.get_crumb_balance()
    return render_template('iteration_loading.html', task_id=task_id, page_uuid=page_uuid,
                           page=page, user=user, crumb_balance=crumb_balance)


@iterations_bp.route('/page/<page_uuid>/iterations')
def get_iterations(page_uuid):
    page = Page.query.filter_by(uuid=page_uuid).first_or_404()
    if page.visibility == 'private' and page.creator_id != session.get('user_id'):
        return jsonify({'error': 'Forbidden'}), 403

    iterations = PageIteration.query.filter_by(page_id=page.id).all()

    def build_node(it):
        return {
            'id': it.id,
            'parent_id': it.parent_iteration_id,
            'author': it.author.username,
            'prompt': it.prompt or '',
            'created_at': it.created_at.isoformat(),
            'iteration_number': it.iteration_number,
            'child_count': len(it.children),
            'is_current': it.id == page.current_iteration_id
        }

    return jsonify([build_node(i) for i in iterations])


@iterations_bp.route('/iteration/<int:iteration_id>')
def get_iteration(iteration_id):
    iteration = PageIteration.query.get_or_404(iteration_id)
    page = iteration.page
    if page.visibility == 'private' and page.creator_id != session.get('user_id'):
        return jsonify({'error': 'Forbidden'}), 403
    return jsonify({
        'id': iteration.id,
        'html_content': iteration.html_content,
        'prompt': iteration.prompt,
        'author': iteration.author.username,
        'created_at': iteration.created_at.isoformat(),
        'iteration_number': iteration.iteration_number
    })


@iterations_bp.route('/iteration/<int:iteration_id>/verdict')
def get_verdict(iteration_id):
    iteration = PageIteration.query.get_or_404(iteration_id)
    page = iteration.page
    if page.visibility == 'private' and page.creator_id != session.get('user_id'):
        return jsonify({'error': 'Forbidden'}), 403
    verdict = WatcherVerdict.query.filter_by(iteration_id=iteration_id).first()
    if not verdict:
        return jsonify({'status': 'pending'})
    return jsonify({
        'status': 'ready',
        'mood': verdict.mood,
        'summary': verdict.summary,
        'points': verdict.points,
        'created_at': verdict.created_at.isoformat()
    })