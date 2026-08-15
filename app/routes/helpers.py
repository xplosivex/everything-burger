from datetime import datetime
from app.models import db, DailyQuest, UserAchievement, Achievement, ACHIEVEMENTS


def update_quest_progress(user_id, quest_type, amount=1):
    quest = db.session.query(DailyQuest).filter(
        DailyQuest.user_id == user_id,
        DailyQuest.quest_type == quest_type,
        DailyQuest.expires_at > datetime.utcnow(),
        DailyQuest.completed == False
    ).first()

    if quest:
        quest.update_progress(amount)
        db.session.commit()


def has_achievement(user_id, achievement_name):
    if achievement_name not in ACHIEVEMENTS:
        return False
    achievement_template = ACHIEVEMENTS[achievement_name]
    existing = db.session.query(UserAchievement).join(Achievement).filter(
        UserAchievement.user_id == user_id,
        Achievement.name == achievement_template['name'],
        UserAchievement.completed == True
    ).first()
    return existing is not None


def update_achievement_progress(user_id, achievement_name, progress_amount):
    from app.models import update_achievement_progress as _uap
    return _uap(user_id, achievement_name, progress_amount)
