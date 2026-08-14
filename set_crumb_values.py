from flask import Flask
import os
from model import (
    User, Page, Vote, Comment, db, get_item_for_user,
    calculate_item_duration, Achievement, UserAchievement, Item, ItemType,
    ItemRarity, ITEMS, RARITY_WEIGHTS, TYPE_WEIGHTS, generate_trinket_details,
    roll_quality, roll_rarity, roll_item_type, get_available_rarities, ActiveEffect,
    ACHIEVEMENTS, update_achievement_progress, grant_achievement, has_achievement,
    check_and_assemble_burger,
    assign_crumb_value_to_existing_items
)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        assign_crumb_value_to_existing_items()
        print("Crumb values have been assigned to all existing items!") 