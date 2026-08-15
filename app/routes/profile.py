import json
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy import func
from serpapi import GoogleSearch
from app.config import SERP_API_KEY
from app.models import db, User, Page, PageIteration, WatcherVerdict
from app.utils import login_required, flash_message
from app.routes.helpers import has_achievement

logger = logging.getLogger(__name__)

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = db.session.query(User).get(session['user_id'])

    if not user:
        flash_message('User not found', 'error')
        return redirect(url_for('generation.dashboard'))

    try:
        # Update bio if provided
        bio = request.form.get('bio')
        if bio is not None:
            user.bio = bio

        # Update featured pages
        # First, clear existing featured pages
        for i in range(1, 4):
            setattr(user, f'featured_page_{i}_id', None)

        # Then set new featured pages
        for i in range(1, 4):
            page_id = request.form.get(f'featured_page_{i}')
            if page_id:
                try:
                    page_id = int(page_id)
                except (TypeError, ValueError):
                    continue
                page = db.session.query(Page).filter_by(id=page_id, creator_id=user.id).first()
                if page:
                    setattr(user, f'featured_page_{i}_id', page.id)
                else:
                    flash_message(f'Featured page {i} not found or unauthorized', 'error')

        # Handle profile picture update
        profile_picture_query = request.form.get('profile_picture_query')
        if profile_picture_query and SERP_API_KEY:
            logger.info(f"Searching for profile picture: {profile_picture_query}")
            try:
                params = {
                    "api_key": SERP_API_KEY,
                    "engine": "google_images",
                    "q": profile_picture_query,
                    "google_domain": "google.com",
                    "hl": "en",
                    "gl": "us",
                    "safe": "off",
                    "num": "1"
                }
                search = GoogleSearch(params)
                results = search.get_dict()
                images = results.get('images_results', [])
                if images:
                    user.profile_picture_url = images[0].get('original', images[0].get('thumbnail', ''))
                    logger.info(f"Successfully fetched profile picture: {user.profile_picture_url}")
                else:
                    logger.error("No image results found in the response")
            except Exception as e:
                logger.error(f"Failed to fetch profile picture: {e}")

        # Handle banner update
        banner_query = request.form.get('banner_query')
        if banner_query and SERP_API_KEY:
            logger.info(f"Searching for banner: {banner_query}")
            try:
                params = {
                    "api_key": SERP_API_KEY,
                    "engine": "google_images",
                    "q": banner_query,
                    "google_domain": "google.com",
                    "hl": "en",
                    "gl": "us",
                    "safe": "off",
                    "num": "1"
                }
                search = GoogleSearch(params)
                results = search.get_dict()
                images = results.get('images_results', [])
                if images:
                    user.banner_url = images[0].get('original', images[0].get('thumbnail', ''))
                    logger.info(f"Successfully fetched banner: {user.banner_url}")
                else:
                    logger.error("No image results found in the response")
            except Exception as e:
                logger.error(f"Failed to fetch banner: {e}")

        db.session.commit()
        flash_message('Profile updated successfully', 'success')

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        flash_message('An error occurred while updating profile', 'error')
        db.session.rollback()

    return redirect(url_for('profile.profile', username=user.username))





@profile_bp.route('/profile/<username>')
@login_required
def profile(username):
    try:
        # Get the viewed user
        viewed_user = db.session.query(User).filter(
            func.lower(User.username) == func.lower(username)
        ).first()
        
        # Get the current logged-in user
        current_user = db.session.query(User).get(session['user_id'])
        
        if not viewed_user:
            flash_message('User not found', 'error')
            return redirect(url_for('generation.dashboard'))

        is_own_profile = viewed_user.id == session.get('user_id')

        # Calculate max slots for viewed user
        max_slots = 40  # Default
        
        if has_achievement(viewed_user.id, 'pro'):
            max_slots = 50
        elif has_achievement(viewed_user.id, 'adept'):
            max_slots = 45
        elif has_achievement(viewed_user.id, 'novice'):
            max_slots = 41

        # Get pages based on visibility rules
        if is_own_profile:
            pages = db.session.query(Page).filter_by(creator_id=viewed_user.id).all()
        else:
            pages = db.session.query(Page).filter_by(
                creator_id=viewed_user.id,
                visibility='public'
            ).all()

        # Get featured pages
        featured_pages = []
        featured_page_1 = viewed_user.featured_page_1
        featured_page_2 = viewed_user.featured_page_2
        featured_page_3 = viewed_user.featured_page_3
        
        if featured_page_1 and (is_own_profile or featured_page_1.visibility == 'public'):
            featured_pages.append(featured_page_1)
        if featured_page_2 and (is_own_profile or featured_page_2.visibility == 'public'):
            featured_pages.append(featured_page_2)
        if featured_page_3 and (is_own_profile or featured_page_3.visibility == 'public'):
            featured_pages.append(featured_page_3)

        # Get current page count
        page_count = len(pages)

        # Set max_pages for the viewed user
        viewed_user.max_pages = max_slots
        crumb_balance = current_user.get_crumb_balance()

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

        return render_template('profile.html',
            user=current_user,
            viewed_user=viewed_user,
            pages=pages,
            featured_pages=featured_pages,
            is_own_profile=is_own_profile,
            max_slots=max_slots,
            page_count=page_count,
            crumb_balance=crumb_balance,
            featured_page_1=featured_page_1,
            featured_page_2=featured_page_2,
            featured_page_3=featured_page_3,
            iteration_counts=iteration_counts,
            watcher_moods=watcher_moods,
            watcher_summaries=watcher_summaries,
            watcher_points=watcher_points
        )

    except Exception as e:
        logger.error(f"Error in profile route: {str(e)}")
        flash_message('An error occurred loading the profile', 'error')
        return redirect(url_for('generation.dashboard'))


@profile_bp.route('/search_users')
def search_users():
    query = request.args.get('q', request.args.get('query', '')).strip()
    if not query or len(query) > 50:
        return jsonify([])

    users = db.session.query(User).filter(User.username.ilike(f'%{query}%')).limit(20).all()

    results = []
    for user in users:
        results.append({
            'username': user.username,
            'profile_picture_url': user.profile_picture_url
        })

    return jsonify(results)
