import uuid
import json
import logging
from flask import Blueprint, render_template, request, url_for, session, jsonify
from app.models import User, Page, PageIteration, WatcherVerdict
from app.utils import login_required
from app.generation.pipeline import get_prompt_length
from app.queue import enqueue

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

    enqueue('iterate', {
        'task_id': task_id,
        'page_uuid': page_uuid,
        'parent_iteration_id': parent_iteration_id,
        'prompt': modification_prompt,
        'user_id': user_id,
    })
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
            'author': it.author.username if it.author else 'Unknown',
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
    meta = None
    if iteration.meta_json:
        try:
            meta = json.loads(iteration.meta_json)
        except (TypeError, ValueError):
            meta = None
    return jsonify({
        'id': iteration.id,
        'html_content': iteration.html_content,
        'prompt': iteration.prompt,
        'author': iteration.author.username if iteration.author else 'Unknown',
        'created_at': iteration.created_at.isoformat(),
        'iteration_number': iteration.iteration_number,
        'meta': meta
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