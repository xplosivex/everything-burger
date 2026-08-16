import json
import os
import time
import uuid
import tempfile
import logging
import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response
from sqlalchemy import func
from selenium import webdriver
from app.extensions import limiter
from app.models import db, User, Page, Vote, Comment, PageIteration, WatcherVerdict, Item
from app.utils import login_required, flash_message
from app.generation.pipeline import get_prompt_length
from app.routes.helpers import update_quest_progress, has_achievement
from app.queue import enqueue

logger = logging.getLogger(__name__)

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/page/<uuid>/thumbnail')
def page_thumbnail(uuid):
    """Serve a page's thumbnail as a real image (Discord embeds can't fetch
    base64 data URIs). Returns the raw PNG stored in thumbnail_url."""
    page = db.session.query(Page).filter_by(uuid=uuid).first()
    if not page or not page.thumbnail_url:
        return ('', 404)
    # thumbnail_url is stored as "data:image/png;base64,..."
    prefix, sep, b64 = page.thumbnail_url.partition(',')
    if not sep:
        return ('', 404)
    mime = 'image/png'
    if 'jpeg' in prefix or 'jpg' in prefix:
        mime = 'image/jpeg'
    elif 'gif' in prefix:
        mime = 'image/gif'
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return ('', 400)
    return Response(raw, mimetype=mime,
                    headers={'Cache-Control': 'public, max-age=3600'})

@pages_bp.route('/pages')
@login_required
def view_pages():
    sort_by = request.args.get('sort', 'views')
    user = db.session.query(User).get(session['user_id'])
    try:
        query = db.session.query(Page).filter(Page.visibility == 'public')

        if sort_by == 'views':
            pages = query.order_by(Page.view_count.desc()).all()
        elif sort_by == 'score':
            pages = query.order_by(Page.score.desc()).all()
        elif sort_by == 'newest':
            pages = query.order_by(Page.created_at.desc()).all()
        else:
            pages = query.order_by(Page.view_count.desc()).all()

        page_ids = [p.id for p in pages]
        iteration_counts = {}
        watcher_moods = {}
        watcher_summaries = {}
        watcher_points = {}
        if page_ids:
            counts = db.session.query(
                PageIteration.page_id,
                func.count(PageIteration.id).label('cnt')
            ).filter(PageIteration.page_id.in_(page_ids)).group_by(PageIteration.page_id).all()
            iteration_counts = {r.page_id: r.cnt for r in counts}
            verdicts = db.session.query(
                Page.id,
                WatcherVerdict.mood,
                WatcherVerdict.summary,
                WatcherVerdict.points_json
            ).join(
                WatcherVerdict, WatcherVerdict.iteration_id == Page.current_iteration_id
            ).filter(Page.id.in_(page_ids)).all()
            watcher_moods = {r[0]: r[1] for r in verdicts}
            watcher_summaries = {r[0]: r[2] for r in verdicts}
            watcher_points = {r[0]: json.loads(r[3]) if r[3] else [] for r in verdicts}

        crumb_balance = user.get_crumb_balance()
        return render_template('pages.html', pages=pages, sort_by=sort_by, user=user,
                               crumb_balance=crumb_balance,
                               iteration_counts=iteration_counts,
                               watcher_moods=watcher_moods,
                               watcher_summaries=watcher_summaries,
                               watcher_points=watcher_points)
    except Exception as e:
        logger.error(f"Error viewing pages: {str(e)}")
        flash_message('An error occurred while loading pages', 'error')
        return redirect(url_for('generation.dashboard'))

@pages_bp.route('/vote/<page_id>/<vote_type>', methods=['POST'])
@login_required
def vote(page_id, vote_type):
    if vote_type not in ['up', 'down']:
        return jsonify({'error': 'Invalid vote type'}), 400

    try:
        page = db.session.query(Page).get(page_id)
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        existing_vote = db.session.query(Vote).filter_by(
            page_id=page_id,
            user_id=session['user_id']
        ).first()

        is_upvote = vote_type == 'up'

        if existing_vote:
            # Remove existing vote if clicking same type
            if existing_vote.is_upvote == is_upvote:
                if is_upvote:
                    page.upvote_count -= 1
                else:
                    page.downvote_count -= 1
                db.session.delete(existing_vote)
            else:
                # Switch vote to the opposite type
                if is_upvote:
                    page.downvote_count -= 1
                    page.upvote_count += 1
                else:
                    page.upvote_count -= 1
                    page.downvote_count += 1
                existing_vote.is_upvote = is_upvote
        else:
            # Add new vote if none exists
            vote = Vote(
                page_id=page_id,
                user_id=session['user_id'],
                is_upvote=is_upvote
            )
            db.session.add(vote)
            if is_upvote:
                page.upvote_count += 1
            else:
                page.downvote_count += 1

        page.score = page.upvote_count - page.downvote_count

        db.session.commit()

        update_quest_progress(session['user_id'], 'send_votes')

        return jsonify({
            'upvotes': page.upvote_count,
            'downvotes': page.downvote_count,
            'score': page.score
        })

    except Exception as e:
        db.session.rollback()

@pages_bp.route('/comment/<page_id>', methods=['POST'])
@login_required
def add_comment(page_id):
    content = request.form.get('content')
    parent_id = request.form.get('parent_id')

    if not content:
        return jsonify({'error': 'Comment content required'}), 400

    try:
        comment = Comment(
            content=content,
            page_id=page_id,
            author_id=session['user_id'],
            parent_id=parent_id if parent_id else None
        )

        db.session.add(comment)
        db.session.commit()

        update_quest_progress(session['user_id'], 'post_comments')

        return jsonify({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.username,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




@pages_bp.route('/page/<uuid>')
def view_page(uuid):
    page = db.session.query(Page).filter_by(uuid=uuid).first()

    if not page:
        flash_message('Page not found', 'error')
        return redirect(url_for('generation.dashboard'))

    # Check visibility permissions
    if page.visibility == 'private':
        if not session.get('user_id') or page.creator_id != session.get('user_id'):
            flash_message('You do not have permission to view this page', 'error')
            return redirect(url_for('generation.dashboard'))

    # Increment view count
    page.view_count += 1
    db.session.commit()

    # Only update quest progress if user is logged in
    if session.get('user_id'):
        update_quest_progress(session['user_id'], 'view_pages')
        user = db.session.query(User).get(session['user_id'])
        crumb_balance = user.get_crumb_balance()
    else:
        user = None
        crumb_balance = 0

    prompt_length = get_prompt_length(session['user_id']) if session.get('user_id') else 175

    from app.config import BASE_URL
    page_url = f"{BASE_URL.rstrip('/')}/page/{page.uuid}"

    # If ?iter=N is present, use that iteration's prompt for the embed
    iter_param = request.args.get('iter', type=int)
    og_description = page.description or page.prompt or 'A page generated with Everything Burger.'
    if iter_param:
        iter_row = PageIteration.query.filter_by(id=iter_param, page_id=page.id).first()
        if iter_row and iter_row.prompt:
            og_description = iter_row.prompt
        page_url = f"{BASE_URL.rstrip('/')}/page/{page.uuid}?iter={iter_param}"

    thumb_url = f"{BASE_URL.rstrip('/')}/page/{page.uuid}/thumbnail"

    context = {
        'page': page,
        'page_url': page_url,
        'thumb_url': thumb_url,
        'og_description': og_description,
        'is_owner': session.get('user_id') == page.creator_id if session.get('user_id') else False,
        'crumb_balance': crumb_balance,
        'user': user,
        'prompt_length': prompt_length
    }
    
    return render_template('page.html', **context)

@pages_bp.route('/save_page', methods=['POST'])
@login_required
def save_page():
    max_slots = 40  # Default
    
    if has_achievement(session['user_id'], 'pro'):
        max_slots = 50  # 40 + 10 from pro
    elif has_achievement(session['user_id'], 'adept'):
        max_slots = 45  # 40 + 5 from adept
    elif has_achievement(session['user_id'], 'novice'):
        max_slots = 41  # 40 + 1 from novice

    # Check if user has reached their slot limit
    user_page_count = db.session.query(Page).filter_by(creator_id=session['user_id']).count()
    if user_page_count >= max_slots:
        flash_message(f'You have reached your maximum limit of {max_slots} saved pages', 'error')
        return redirect(url_for('generation.dashboard'))
        
    title = (request.form.get('title') or '').strip()
    description = request.form.get('description', '')
    html_content = request.form.get('html_content')
    prompt = request.form.get('prompt', '')
    archetype = request.form.get('archetype', '')
    meta_raw = request.form.get('meta', '')
    visibility = request.form.get('visibility', 'public')
    tags = request.form.get('tags', '')

    if not title:
        flash_message('Page title is required', 'error')
        return redirect(url_for('generation.dashboard'))

    if visibility not in ('public', 'private', 'unlisted'):
        visibility = 'public'

    if not html_content:
        flash_message('Page content is required', 'error')
        return redirect(url_for('generation.dashboard'))

    # Generate thumbnail from HTML content
    try:
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(html_content.encode())
            temp_path = f.name

        # Use Selenium to take screenshot
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.get('file://' + temp_path)
        driver.set_window_size(1200, 800)

        # Wait for page to load and render
        time.sleep(3)  # Wait 3 seconds for content to render

        # Take screenshot and save as base64
        screenshot = driver.get_screenshot_as_base64()
        thumbnail_url = f"data:image/png;base64,{screenshot}"

        driver.quit()
        os.unlink(temp_path)
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        thumbnail_url = ''

    # Create new page
    page = Page(
        title=title,
        description=description,
        html_content=html_content,
        prompt=prompt,
        archetype=archetype or None,
        meta_json=meta_raw or None,
        visibility=visibility,
        tags=tags,
        thumbnail_url=thumbnail_url,
        creator_id=session['user_id']
    )

    db.session.add(page)
    db.session.commit()

    root_iteration = PageIteration(
        page_id=page.id,
        parent_iteration_id=None,
        html_content=html_content,
        prompt=prompt,
        author_id=session['user_id'],
        iteration_number=0,
        meta_json=meta_raw or None
    )
    db.session.add(root_iteration)
    db.session.flush()
    page.current_iteration_id = root_iteration.id
    db.session.commit()
    enqueue('watcher_verdict', {'iteration_id': root_iteration.id})

    page_uuid = page.uuid # Get UUID before closing session

    # Calculate crumb reward for saving
    base_save_crumbs = 10  # Base crumbs for saving a page
    
    # Check for Crumb Harvester artifact
    has_crumb_harvester = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Crumb Harvester"
    ).first() is not None

    total_save_crumbs = base_save_crumbs
    if has_crumb_harvester:
        total_save_crumbs = int(base_save_crumbs * 1.3)  # 30% bonus from Crumb Harvester

    # Add crumbs to user
    user = db.session.query(User).filter_by(id=session['user_id']).first()
    if user:
        user.add_crumbs(total_save_crumbs)
        logger.info(f"Awarded {total_save_crumbs} crumbs to user {session['user_id']} for saving page")

    # Add XP based on HTML content length
    content_length = len(html_content)
    xp_reward = content_length // 100  # 1 XP per 100 characters
    
    # Add XP for saving a page
    xp_reward += 50
    
    # Add XP if it's a multiple of 10 generations
    user = db.session.query(User).get(session['user_id'])

        
    user.add_xp(xp_reward)
    db.session.commit()

    flash_message('Page saved successfully', 'success')
    update_quest_progress(session['user_id'], 'save_pages')
    return redirect(url_for('pages.view_page', uuid=page_uuid))


@pages_bp.route('/page/<page_id>/visibility', methods=['POST'])
@login_required
def toggle_visibility(page_id):
    page = db.session.query(Page).filter_by(id=page_id).first()

    if not page or page.creator_id != session.get('user_id'):
        flash_message('Page not found or unauthorized', 'error')
        return redirect(url_for('generation.dashboard'))

    # Get creator username before closing session
    creator_username = db.session.query(User).get(page.creator_id).username

    # Cycle through visibility states: public -> unlisted -> private -> public
    if page.visibility == 'public':
        page.visibility = 'unlisted'
    elif page.visibility == 'unlisted':
        page.visibility = 'private'
    else:
        page.visibility = 'public'

    db.session.commit()

    flash_message('Page visibility updated', 'success')
    return redirect(url_for('profile.profile', username=creator_username))

@pages_bp.route('/page/<page_id>/delete', methods=['POST'])
@login_required
def delete_page(page_id):
    page = db.session.query(Page).filter_by(id=page_id).first()

    if not page or page.creator_id != session.get('user_id'):
        flash_message('Page not found or unauthorized', 'error')
        return redirect(url_for('generation.dashboard'))

    # Get creator username before deleting
    creator_username = page.creator.username

    # Remove page from featured if needed
    creator = page.creator
    if creator.featured_page_1_id == page.id:
        creator.featured_page_1_id = None
    if creator.featured_page_2_id == page.id:
        creator.featured_page_2_id = None
    if creator.featured_page_3_id == page.id:
        creator.featured_page_3_id = None

    db.session.delete(page)
    db.session.commit()

    flash_message('Page deleted successfully', 'success')
    return redirect(url_for('profile.profile', username=creator_username))