import re
import logging
from datetime import datetime
import pytz
from app.models import db, Item, User, update_achievement_progress

logger = logging.getLogger(__name__)

def check_generation_achievements(soup, user_id, prompt, num_images):
    """Run all achievement checks on generated content."""
    html_str = str(soup).lower()
    clean_prompt = re.sub(r'[^a-zA-Z]', '', prompt.lower())

    checks = [
        ('magic_caster', 'wizard' in html_str and 'wizard' not in clean_prompt),
        ('certified_programmer', '<script>' in html_str or 'javascript:' in html_str),
        ('invisible_ink', _check_invisible_ink(html_str)),
        ('paparazzi', num_images >= 4),
        ('meme_lord', 'rick roll' in html_str or 'never gonna give you up' in html_str),
        ('bug_hunter', 'error' in html_str or 'bug' in html_str),
        ('mr_ocd', '<ul>' in html_str or '<ol>' in html_str),
        ('poop_wizard', 'poop' in html_str and 'wizard' in html_str
                        and 'poop' not in clean_prompt and 'wizard' not in clean_prompt),
        ('digestive_mistro', 'poop' in prompt.lower()),
    ]

    for achievement_id, condition in checks:
        if condition:
            update_achievement_progress(user_id, achievement_id, 1)

    est_time = datetime.now(pytz.timezone('US/Eastern'))
    if 2 <= est_time.hour < 4:
        update_achievement_progress(user_id, 'night_owl', 1)

    if num_images >= 4:
        update_achievement_progress(user_id, 'paparazzi', num_images)


def _check_invisible_ink(html_str):
    white_text = any(x in html_str for x in [
        'color: white', 'color: #fff', 'color: #ffffff', 'text-white'
    ])
    white_bg = any(x in html_str for x in [
        'background: white', 'background: #fff', 'background: #ffffff',
        'background-color: white', 'background-color: #fff',
        'background-color: #ffffff', 'bg-white'
    ])
    return white_text and white_bg


def award_generation_rewards(user_id, html_content: str):
    """Calculate and award crumbs + XP for content generation."""
    content_length = len(html_content)

    base_crumbs = (content_length // 1000) * 5
    bonus_crumbs = (content_length // 2000) * 2
    total_crumbs = base_crumbs + bonus_crumbs

    has_harvester = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name == "Crumb Harvester"
    ).first() is not None

    if has_harvester:
        total_crumbs = int(total_crumbs * 1.3)

    content_xp = content_length // 100

    user = db.session.query(User).get(user_id)
    if user and total_crumbs > 0:
        user.add_crumbs(total_crumbs)
        user.add_xp(content_xp)
        logger.info(f"Awarded {total_crumbs} crumbs, {content_xp} XP to user {user_id}")
