import random
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, session
import pytz
from app.models import db, User, Page, UserAchievement, Achievement, ACHIEVEMENTS, DAILY_QUEST_TYPES, DailyQuest, update_achievement_progress
from app.utils import login_required

logger = logging.getLogger(__name__)

achievements_bp = Blueprint('achievements', __name__)

@achievements_bp.route('/achievements')
@login_required
def achievements():


    # Get highest viewed page for the user
    highest_viewed_page = db.session.query(Page).filter(
        Page.creator_id == session['user_id']
    ).order_by(Page.view_count.desc()).first()

    if highest_viewed_page:
        # Update the 'celebrity' achievement progress with the highest view count
        update_achievement_progress(
            session['user_id'],
            'celebrity',
            highest_viewed_page.view_count
        )


    # Get user's achievements from database
    user_achievements = db.session.query(UserAchievement).filter(
        UserAchievement.user_id == session['user_id']
    ).join(Achievement).all()
    
    # Create a lookup dictionary for quick access to user achievements
    user_achievements_dict = {
        ua.achievement.name: ua for ua in user_achievements
    }
    
    # Format achievements for display, starting with ACHIEVEMENTS dictionary
    achievements_data = []
    
    for achievement_id, achievement_info in ACHIEVEMENTS.items():
        # Find matching user achievement if it exists
        user_achievement = user_achievements_dict.get(achievement_info['name'])
        
        # Extract reward text and clean description if reward exists
        reward_text = None
        description = achievement_info['description']
        if 'Reward:' in description:
            parts = description.split('Reward:')
            description = parts[0].strip()
            reward_text = parts[1].strip()
        
        achievement_data = {
            'name': achievement_info['name'],
            'description': description,
            'requirement_count': achievement_info['requirement_count'],
            'reward_type': achievement_info['reward_type'],
            'reward_amount': achievement_info['reward_amount'],
            'reward_text': reward_text,
            # Use user achievement data if it exists, otherwise default values
            'progress': user_achievement.progress if user_achievement else 0,
            'completed': user_achievement.completed if user_achievement else False,
            'completed_at': user_achievement.completed_at if user_achievement else None
        }
        achievements_data.append(achievement_data)

    # Sort by completion status and name
    achievements_data.sort(key=lambda x: (-int(x['completed']), x['name']))
    user = db.session.query(User).get(session['user_id'])
    crumb_balance = user.get_crumb_balance()   

    # Get user's active daily quests
    daily_quests = db.session.query(DailyQuest).filter(
        DailyQuest.user_id == session['user_id'],
        DailyQuest.expires_at > datetime.utcnow()
    ).all()

    # If no active quests or existing quests are expired, generate new ones
    if not daily_quests:
        daily_quests = generate_daily_quests(session['user_id'])

    # Format quests for display
    quests_data = []
    for quest in daily_quests:
        quest_info = DAILY_QUEST_TYPES[quest.quest_type]
        quests_data.append({
            'name': quest_info['name'],
            'description': quest_info['description'].format(
                count=quest.target_amount,
                threshold=quest_info.get('threshold', '')
            ),
            'progress': quest.current_progress,
            'target': quest.target_amount,
            'reward_type': quest.reward_type,
            'reward_amount': quest.reward_amount,
            'completed': quest.completed,
            'expires_at': quest.expires_at
        })

    return render_template(
        'achievements.html',
        achievements=achievements_data,
        daily_quests=quests_data,
        crumb_balance=crumb_balance,
        user=user
    )


def generate_daily_quests(user_id):
    logger.info(f"Generating daily quests for user {user_id}")
    
    # Get existing non-expired quests using UTC for comparison
    existing_quests = db.session.query(DailyQuest).filter(
        DailyQuest.user_id == user_id,
        DailyQuest.expires_at > datetime.utcnow()  # Already using UTC
    ).all()
    
    # If user has non-expired quests, return those instead of generating new ones
    if existing_quests:
        logger.info(f"User {user_id} has {len(existing_quests)} active quests, returning those")
        return existing_quests

    # Delete any expired quests
    deleted = db.session.query(DailyQuest).filter(
        DailyQuest.user_id == user_id,
        DailyQuest.expires_at <= datetime.utcnow()
    ).delete()
    logger.info(f"Deleted {deleted} expired quests")

    # Calculate next expiration time (12 PM or 12 AM EST)
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    # Create naive datetime for target time
    if now.hour < 12:
        target_time = datetime(
            now.year, now.month, now.day, 
            12, 0, 0, 0
        )
    else:
        tomorrow = now + timedelta(days=1)
        target_time = datetime(
            tomorrow.year, tomorrow.month, tomorrow.day, 
            0, 0, 0, 0
        )
    
    # Localize the naive datetime to EST, then convert to UTC
    expires_at = est.localize(target_time).astimezone(pytz.UTC).replace(tzinfo=None)
    logger.info(f"Set expiration time to {expires_at} UTC")

    # Select 3 random quest types
    selected_types = random.sample(list(DAILY_QUEST_TYPES.keys()), 3)
    logger.info(f"Selected quest types: {selected_types}")
    
    # Get user's current level
    user = db.session.query(User).get(user_id)
    
    new_quests = []
    for quest_type in selected_types:
        quest_info = DAILY_QUEST_TYPES[quest_type]
        target_amount = random.randint(quest_info['min_count'], quest_info['max_count'])
        
        # Calculate rewards - crumbs stay fixed but XP scales with level
        reward_crumbs = quest_info['base_crumbs'] * target_amount
        reward_xp = int(quest_info['base_xp'] * target_amount * (1 + (user.level - 1) * 0.1))

        logger.info(f"Creating quest of type {quest_type} with target {target_amount}")
        logger.info(f"Rewards: {reward_crumbs} crumbs, {reward_xp} XP")

        quest = DailyQuest(
            user_id=user_id,
            quest_type=quest_type,
            target_amount=target_amount,
            reward_type='both',  # Will give both crumbs and xp
            reward_amount=reward_crumbs,  # Store crumbs amount, XP will be half
            expires_at=expires_at
        )
        db.session.add(quest)
        new_quests.append(quest)
    
    db.session.commit()
    logger.info(f"Generated {len(new_quests)} new daily quests")
    return new_quests