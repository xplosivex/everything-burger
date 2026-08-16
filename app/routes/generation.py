import uuid
import random
import logging
from sqlalchemy import func, text
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from app.extensions import limiter
from app.models import db, User, Item, ItemType, Page, PageIteration, WatcherVerdict, Achievement, UserAchievement, ACHIEVEMENTS, update_achievement_progress, has_achievement, get_item_for_user, calculate_item_duration, Comment, Vote
from app.utils import login_required, flash_message
from app.state import put, get, contains, count_active_generations
from app.generation.pipeline import get_prompt_length
from app.routes.helpers import update_quest_progress
from app.queue import enqueue

logger = logging.getLogger(__name__)

generation_bp = Blueprint('generation', __name__)

@generation_bp.route('/')
@login_required
def dashboard():

    user = db.session.query(User).get(session['user_id'])
    crumb_balance = user.get_crumb_balance()
    logger.info(f"Crumb balance: {crumb_balance}")


    # Default prompt length calculation (unchanged)
    prompt_length = 175

    has_keyboard = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Terrys Keyboard"
    ).first() is not None

    if has_keyboard:
        prompt_length += 50

    active_effects = Item.get_active_effects(session['user_id'])
    for effect in active_effects:
        if effect.effect_type == 'prompt_length':
            prompt_length += int(float(effect.effect_value))

    try:
        # Calculate global statistics
        total_users = db.session.query(User).count()
        total_generations = db.session.query(func.sum(User.pages_generated)).scalar() or 0
        total_saved_pages = db.session.query(Page).count()
        total_comments = db.session.query(Comment).count()
        total_votes = db.session.query(Vote).count()

        # Get most active user (by pages generated)
        most_active_user = db.session.query(
            User.username,
            User.pages_generated
        ).order_by(
            User.pages_generated.desc()
        ).first()

        # Get user with most upvotes on their pages
        most_upvoted_user = db.session.query(
            User.username,
            func.sum(Page.upvote_count).label('total_upvotes')
        ).join(Page, User.id == Page.creator_id).group_by(User.id).order_by(
            text('total_upvotes DESC')
        ).first()

        # Get most viewed page
        most_viewed_page = db.session.query(
            Page.title,
            Page.view_count
        ).order_by(
            Page.view_count.desc()
        ).first()

        

        # Calculate user statistics
        user = db.session.get(User, session['user_id'])
        user_stats = {
            'total_pages_generated': user.pages_generated,
            'total_saved_pages': db.session.query(Page).filter(Page.creator_id == session['user_id']).count(),
            'total_comments': db.session.query(Comment).filter(Comment.author_id == session['user_id']).count(),
            'total_votes': db.session.query(Vote).filter(Vote.user_id == session['user_id']).count()
        }

        stats = {
            'total_users': total_users,
            'total_generations': total_generations,
            'total_saved_pages': total_saved_pages,
            'total_comments': total_comments,
            'total_votes': total_votes,
            'most_active_user': most_active_user,
            'most_upvoted_user': most_upvoted_user,
            'most_viewed_page': most_viewed_page,
            'user_stats': user_stats
        }

    except Exception as e:
        logger.error(f"Error generating dashboard stats: {str(e)}")
        stats = {
            'total_users': 0,
            'total_generations': 0,
            'total_saved_pages': 0,
            'total_comments': 0,
            'total_votes': 0,
            'most_active_user': None,
            'most_upvoted_user': None,
            'most_viewed_page': None,
            'user_stats': {
                'total_pages_generated': 0,
                'total_saved_pages': 0,
                'total_comments': 0,
                'total_votes': 0
            }
        }
        flash_message('Error loading statistics', 'error')

    logger.info("Dashboard page requested with global and user stats")
    return render_template(
        'dashboard.html',
        prompt_length=prompt_length,
        stats=stats,
        crumb_balance=crumb_balance,
        user=user
    )


def try_reward_item(user_id, prompt=None):
    base_chance = 0.45

    logger.info(f"Attempting item reward roll for user {user_id}")
    logger.info(f"Base chance: {base_chance}")

    # Check for active item_chance effects
    active_effects = Item.get_active_effects(user_id)
    chance_multiplier = 1.0

    for effect in active_effects:
        if effect.effect_type == 'item_chance':
            chance_multiplier *= float(effect.effect_value)
            logger.info(f"Applied item_chance effect: {effect.effect_value}x multiplier")

    final_chance = base_chance * chance_multiplier
    logger.info(f"Final item chance after multipliers: {final_chance}")

    roll = random.random()
    logger.info(f"Random roll: {roll}")

    if roll < final_chance:  # Adjusted chance
        logger.info(f"Successful item roll! (Roll: {roll} < Chance: {final_chance})")
        try:
            item = get_item_for_user(user_id, prompt)
            logger.info(f"Generated item: {item.name} ({item.rarity.value})")

            # Set duration based on item type
            if item.type == ItemType.CONSUMABLE:
                if item.effect_duration:
                    item.effect_duration = calculate_item_duration(
                        item.effect_duration,
                        item.quality,
                        item.rarity,
                        user_id
                    )
                    logger.info(f"Set consumable duration to {item.effect_duration}")
            elif item.type == ItemType.TRINKET:
                item.uses_remaining = 1
                item.effect_duration = None
                logger.info("Set trinket with 1 use remaining")
            else:  # Artifact
                item.uses_remaining = None
                item.effect_duration = None
                logger.info("Set artifact with unlimited duration")

            db.session.add(item)
            db.session.commit()
            logger.info(f"Successfully saved item {item.id} to database")

            # Add XP based on item rarity
            user = db.session.query(User).get(user_id)
            rarity_xp = {
                'common': 25,
                'rare': 50,
                'epic': 100,
                'legendary': 200,
                'mythical': 500
            }
            user.add_xp(rarity_xp.get(item.rarity.value.lower(), 25))

            # Check for quality items quest
            if item.quality > 75:
                update_quest_progress(user_id, 'quality_items')

            # Notify the user (no-op in background workers without a request context)
            flash_message(f'You received a {item.rarity.value.lower()} {item.type.value.lower()}: {item.name}!', 'success')
            logger.info(f"Sent item received message to user {user_id}")

        except Exception as e:
            logger.error(f"Error rewarding random item: {str(e)}")
            logger.exception("Full exception details:")
    else:
        logger.info(f"Failed item roll (Roll: {roll} >= Chance: {final_chance})")

@generation_bp.route('/use_item/<int:item_id>', methods=['POST'])
@login_required
def use_item(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()

    if not item:
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory.inventory'))

    success, message = item.use(session['user_id'])

    if success:
        if item.type == ItemType.CONSUMABLE:
            update_quest_progress(session['user_id'], 'use_consumables')
        flash_message(message, 'success')
    else:
        flash_message(message, 'error')

    return redirect(url_for('inventory.inventory'))



def _handle_generation(prompt, user_id, task_id):
    prompt = (prompt or '').strip()
    if not prompt:
        flash_message('Please enter a prompt to generate a page', 'error')
        return redirect(url_for('generation.dashboard'))

    # Check active generations limit
    if count_active_generations(user_id) >= 3:
        flash_message('You can only have 3 active generations at a time. Please wait for existing generations to complete.', 'error')
        return redirect(url_for('generation.dashboard'))

    with current_app.app_context():
        put(task_id, {
            'html': None,
            'prompt': prompt,
            'completed': False,
            'error': None,
            'user_id': user_id  # Add user_id to track ownership
        })

        user = db.session.get(User, user_id)
        user.pages_generated += 1
        db.session.commit()

        # Check for digestive_mistro achievement
        if 'poop' in prompt.lower():
            update_achievement_progress(user_id, 'digestive_mistro', 1)

        # Check for achievement progress
        update_achievement_progress(user_id, 'novice', user.pages_generated)
        update_achievement_progress(user_id, 'adept', user.pages_generated)
        update_achievement_progress(user_id, 'pro', user.pages_generated)
        
        # Check for burger_beholder achievement
        # Only check if they've generated enough pages
        if user.pages_generated >= 250:
            # Count completed achievements
            completed_achievements = db.session.query(UserAchievement).join(Achievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.completed == True
            ).count()
            
            # Get total number of achievements
            total_achievements = len(ACHIEVEMENTS)
            
            # If they have completed half or more achievements
            if completed_achievements >= total_achievements / 2:
                update_achievement_progress(user_id, 'burger_beholder', 1)

        # Check for buffed_generation achievement
        active_effects = Item.get_active_effects(user_id)
        if active_effects:
            update_achievement_progress(user_id, 'buffed_generation', 1)

        update_quest_progress(user_id, 'generate_pages')

        try_reward_item(user_id, prompt)

    enqueue('generate', {'task_id': task_id, 'prompt': prompt, 'user_id': user_id})
    return redirect(url_for('generation.result', task_id=task_id))

@generation_bp.route('/generate', methods=['POST'])
@login_required
@limiter.limit('60 per minute')
def generate():
    user_input = (request.form.get('prompt') or '').strip()
    if not user_input:
        flash_message('Please enter a prompt to generate a page', 'error')
        return redirect(url_for('generation.dashboard'))
    task_id = str(uuid.uuid4())
    user_id = session['user_id']
    logger.info(f"New generation request. Task ID: {task_id}")
    return _handle_generation(user_input, user_id, task_id)

@generation_bp.route('/regenerate/<task_id>', methods=['POST'])
@login_required
@limiter.limit('60 per minute')
def regenerate(task_id):
    logger.info(f"Regeneration requested for task {task_id}")
    if not contains(task_id):
        logger.warning(f"Task {task_id} not found for regeneration")
        return redirect(url_for('generation.dashboard'))

    content = get(task_id)
    if content['user_id'] != session['user_id']:
        flash_message('Unauthorized access to generation result', 'error')
        return redirect(url_for('generation.dashboard'))

    prompt = content['prompt']
    new_task_id = str(uuid.uuid4())
    user_id = session['user_id']
    logger.info(f"Created new task {new_task_id} for regeneration")
    return _handle_generation(prompt, user_id, new_task_id)

@generation_bp.route('/result/<task_id>')
@login_required
def result(task_id):
    logger.info(f"Result page requested for task {task_id}")
    if not contains(task_id):
        logger.info(f"Task {task_id} not found")
        flash_message('Invalid or expired task ID', 'error')
        return redirect(url_for('generation.dashboard'))

    content = get(task_id)
    
    # Verify the generation belongs to the current user
    if content['user_id'] != session['user_id']:
        flash_message('Unauthorized access to generation result', 'error')
        return redirect(url_for('generation.dashboard'))

    if content['error']:
        html_content = f"An error occurred: {content['error']}"
    else:
        html_content = "Generation in progress..." if not content['completed'] else content['html']

    return render_template('result.html',
                         html_content=html_content,
                         prompt=content['prompt'],
                         archetype=content.get('archetype', ''),
                         meta=content.get('meta'),
                         task_id=task_id)