from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
import random
import os
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from app.ai import complete
db = SQLAlchemy()

class ItemRarity(enum.Enum):
    COMMON = 'common'
    RARE = 'rare'
    EPIC = 'epic'
    LEGENDARY = 'legendary'
    MYTHICAL = 'mythical'

class ItemType(enum.Enum):
    CONSUMABLE = 'consumable'
    ARTIFACT = 'artifact'
    TRINKET = 'trinket'

RARITY_WEIGHTS = {
    ItemRarity.COMMON: 0.4,
    ItemRarity.RARE: 0.3,
    ItemRarity.EPIC: 0.15,
    ItemRarity.LEGENDARY: 0.1,
    ItemRarity.MYTHICAL: 0.05
}

TYPE_WEIGHTS = {
    ItemType.CONSUMABLE: 0.4,
    ItemType.ARTIFACT: 0.2,
    ItemType.TRINKET: 0.4
}

RARITY_PRICES = {
    ItemRarity.COMMON: 1,
    ItemRarity.RARE: 2,
    ItemRarity.EPIC: 3,
    ItemRarity.LEGENDARY: 4,
    ItemRarity.MYTHICAL: 5
}

def calculate_shop_price(item_data, discount=None):
    base_price = 250 if item_data['type'] == ItemType.ARTIFACT else 100
    rarity_multiplier = RARITY_PRICES[item_data['rarity']]
    original_price = base_price * rarity_multiplier
    
    if discount:
        try:
            # Convert discount effect_value to float and ensure it's a valid number
            discount_multiplier = float(str(discount.effect_value).strip())
            discounted_price = int(original_price * discount_multiplier)
            return {
                'original': original_price,
                'discounted': discounted_price
            }
        except (ValueError, TypeError):
            # If there's any error parsing the discount, return original price
            logger.error(f"Invalid discount value: {discount.effect_value}")
            return {
                'original': original_price,
                'discounted': None
            }
    
    return {
        'original': original_price,
        'discounted': None
    }

SHOP_ITEMS = {
    'dopamine_enhancer': {
        'name': 'Dopamine Enhancer',
        'description': 'While this artifact is unlocked, permanently increases the crumb value of all items',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.EPIC,
        'effect_type': 'crumb_multiplier',
        'effect_value': 1.5
    },
    'trading_stick': {
        'name': 'Trading Stick',
        'description': 'While this artifact is unlocked, all trade-ups below legendary rarity only require 2 items',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.LEGENDARY,
        'effect_type': 'trade_requirement',
        'effect_value': 2
    },
    'crumb_harvester': {
        'name': 'Crumb Harvester',
        'description': 'While this artifact is unlocked, gain additional crumbs when generating or saving pages',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.RARE,
        'effect_type': 'crumb_gain',
        'effect_value': 1.3
    },
    'big_brain_juice': {
        'name': 'Big Brain Juice',
        'description': 'Makes generated pages sound like a scholarly intellectual who definitely watches Rick and Morty. Note: You may only have one generation style active at a time. Available styles: Big Brain Juice, Wizard\'s Beard Oil, Pegleg Polish',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.RARE,
        'effect_type': 'generation_style',
        'effect_value': 'intellectual',
        'effect_duration': 3600,
        'uses_remaining': 2  # RARE
    },
    'wizards_beard_oil': {
        'name': "Wizard's Beard Oil", 
        'description': 'Makes generated pages sound like they were written by a whimsical wizard who had too much coffee. Note: You may only have one generation style active at a time. Available styles: Big Brain Juice, Wizard\'s Beard Oil, Pegleg Polish',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.RARE,
        'effect_type': 'generation_style',
        'effect_value': 'wizard',
        'effect_duration': 3600,
        'uses_remaining': 2  # RARE
    },
    'pegleg_polish': {
        'name': 'Pegleg Polish',
        'description': 'Yarr! Makes generated pages sound like they were written by a pirate who found a keyboard. Note: You may only have one generation style active at a time. Available styles: Big Brain Juice, Wizard\'s Beard Oil, Pegleg Polish',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.RARE,
        'effect_type': 'generation_style',
        'effect_value': 'pirate',
        'effect_duration': 3600,
        'uses_remaining': 2  # RARE
    },
    'stonks_potion': {
        'name': 'Stonks Potion',
        'description': 'While active, reduces all shop prices by 10% because who doesn\'t love a good deal',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.EPIC,
        'effect_type': 'shop_discount',
        'effect_value': 0.85,
        'effect_duration': 3600,
        'uses_remaining': 3  # EPIC
    },
    'rainbow_ink': {
        'name': 'Rainbow Ink',
        'description': 'While active, makes each paragraph a different color because why not make reading more fun',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'paragraph_colors',
        'effect_value': True,
        'effect_duration': 3600,
        'uses_remaining': 1  # COMMON
    },
    'math_teachers_revenge': {
        'name': "Math Teacher's Revenge",
        'description': 'Replaces all numbers with unnecessarily complex calculations that equal the same number',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'number_replacement',
        'effect_value': True,
        'effect_duration': 3600,
        'uses_remaining': 1  # COMMON
    },
    'glowie_glasses': {
        'name': 'Glowie Glasses',
        'description': 'Attempts to make text and images glow green',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'green_glow',
        'effect_value': True,
        'effect_duration': 3600,
        'uses_remaining': 1  # COMMON
    },
    'dragon_cursor': {
        'name': 'Dragon Cursor',
        'description': 'Upon using this item, your cursor becomes a dragon scimitar from Old School RuneScape',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.LEGENDARY,
        'effect_type': 'cursor',
        'effect_value': 'dragon_scimitar',
        'effect_duration': 3600,
        'uses_remaining': 4  # LEGENDARY
    },
    'cleansing_potion': {
        'name': 'Cleansing Potion',
        'description': 'This clears all active consumable boosts',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'clear_boosts',
        'effect_value': 1,
        'effect_duration': 0,
        'uses_remaining': 1  # COMMON
    }
}

ITEMS = {
    'magic_milk': {
        'name': 'Magic Milk',
        'description': 'While this is active you have a greater chance of receiving items',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'item_chance',
        'effect_value': 1.5,
        'effect_duration': 3600
    },
    'boomer_glasses': {
        'name': 'Boomer Glasses', 
        'description': 'While active this makes all text generated on your pages bigger',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'font_size',
        'effect_value': 2.3,
        'effect_duration': 3600
    },
    'cleansing_potion': {
        'name': 'Cleansing Potion',
        'description': 'This clears all active consumable boosts',
        'type': ItemType.CONSUMABLE, 
        'effect_type': 'clear_boosts',
        'effect_value': 1,
        'effect_duration': 0
    },
    'product_placement': {
        'name': 'Product Placement',
        'description': 'Increases the amount of photos on any page generated',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'image_count',
        'effect_value': 2,
        'effect_duration': 3600
    },
    'silly_little_guy': {
        'name': 'Silly Little Guy',
        'description': 'Makes all pages generate in comic sans',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'font_family',
        'effect_value': 'Comic Sans MS',
        'effect_duration': 3600
    },
    'magic_mushrooms': {
        'name': 'Magic Mushrooms',
        'description': 'Makes the page more sporadic and unpredictable',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'randomness',
        'effect_value': 1.5,
        'effect_duration': 3600
    },
    'seconds_please': {
        'name': 'Seconds Please',
        'description': 'Extra 100 Character for the initial prompt',
        'type': ItemType.CONSUMABLE,
        'effect_type': 'prompt_length',
        'effect_value': 100,
        'effect_duration': 3600
    },
    'sesame_seed': {
        'name': 'Sesame Seed',
        'description': 'While this item is unlocked you can have up to two consumable boosts active',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'max_consumables',
        'effect_value': 2
    },
    'terrys_keyboard': {
        'name': 'Terrys Keyboard',
        'description': 'Allows an extra 50 characters for the initial prompt while this is unlocked',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.COMMON,
        'effect_type': 'prompt_length',
        'effect_value': 50
    },
    'time_whisperer': {
        'name': 'Time Whisperer',
        'description': 'While this item is unlocked extends the duration of consumables',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.RARE,
        'effect_type': 'duration_multiplier',
        'effect_value': 1.5
    },
    'goblet_of_wok': {
        'name': 'Goblet of Wok',
        'description': 'When this item is unlocked you are guaranteed an extra 5000 tokens for your page generation',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.RARE,
        'effect_type': 'token_count',
        'effect_value': 5000
    },
    'bag_of_holding': {
        'name': 'Bag of Holding',
        'description': 'While this is unlocked allows a user to store an extra 10 pages',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.EPIC,
        'effect_type': 'max_pages',
        'effect_value': 10
    },
    'lucky_horseshoe': {
        'name': 'Lucky Horseshoe',
        'description': 'While this item is unlocked there is a higher chance of rare items',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.EPIC,
        'effect_type': 'rarity_chance',
        'effect_value': 1.5
    },
    'gamblers_odds': {
        'name': "Gambler's Odds",
        'description': 'While this item is unlocked raises the chances of successfully completing a trade up',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.LEGENDARY,
        'effect_type': 'trade_up_chance',
        'effect_value': 1.5
    },
    'bun_fragment': {
        'name': 'Bun Fragment',
        'description': 'A mystical fragment of the legendary Everything Burger. Collect all 5 fragments to assemble it.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'fragment',
        'effect_value': 'bun'
    },
    'patty_fragment': {
        'name': 'Patty Fragment',
        'description': 'A mystical fragment of the legendary Everything Burger. Collect all 5 fragments to assemble it.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'fragment',
        'effect_value': 'patty'
    },
    'ketchup_fragment': {
        'name': 'Ketchup Fragment',
        'description': 'A mystical fragment of the legendary Everything Burger. Collect all 5 fragments to assemble it.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'fragment',
        'effect_value': 'ketchup'
    },
    'pickle_fragment': {
        'name': 'Pickle Fragment',
        'description': 'A mystical fragment of the legendary Everything Burger. Collect all 5 fragments to assemble it.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'fragment',
        'effect_value': 'pickle'
    },
    'cheese_fragment': {
        'name': 'Cheese Fragment',
        'description': 'A mystical fragment of the legendary Everything Burger. Collect all 5 fragments to assemble it.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'fragment',
        'effect_value': 'cheese'
    },
    'everything_burger': {
        'name': 'Everything Burger',
        'description': 'The legendary Everything Burger, assembled from 5 mythical fragments. Its power is beyond comprehension.',
        'type': ItemType.ARTIFACT,
        'rarity': ItemRarity.MYTHICAL,
        'effect_type': 'burger',
        'effect_value': 0  # This will be used to track +1, +2, etc.
    }
}

ACHIEVEMENTS = {
    'novice': {
        'name': 'Novice',
        'description': 'Generate 10 pages. Reward: 1 save slot',
        'requirement_type': 'pages_generated',
        'requirement_count': 10,
        'reward_type': 'save_slots',
        'reward_amount': 1
    },
    'adept': {
        'name': 'Adept', 
        'description': 'Generate 50 pages. Reward: 5 save slots',
        'requirement_type': 'pages_generated',
        'requirement_count': 50,
        'reward_type': 'save_slots',
        'reward_amount': 5
    },
    'pro': {
        'name': 'Pro',
        'description': 'Generate 100 pages. Reward: 10 save slots',
        'requirement_type': 'pages_generated',
        'requirement_count': 100,
        'reward_type': 'save_slots',
        'reward_amount': 10
    },
    'hobbyist': {
        'name': 'Hobbyist',
        'description': 'Have 15 items in your inventory. Reward: Unlock trade-ups',
        'requirement_type': 'inventory_count',
        'requirement_count': 15,
        'reward_type': 'unlock_tradeups',
        'reward_amount': 1
    },
    'collector': {
        'name': 'Collector',
        'description': 'Obtain a trinket of each rarity. Reward: Unlocks the ability to roll a Burger Fragment when rolling for an item',
        'requirement_type': 'trinket_col0lection',
        'requirement_count': 4,  # One of each non-mythical rarity
        'reward_type': 'unlock_fragments',
        'reward_amount': 1
    },
    'chad_status': {
        'name': 'Chad Status',
        'description': 'Obtain the Everything Burger',
        'requirement_type': 'obtain_burger',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'magic_caster': {
        'name': 'Magic Caster',
        'description': 'Generate a page containing "wizard" without using it in the prompt',
        'requirement_type': 'special_content',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'certified_programmer': {
        'name': 'Certified Programmer',
        'description': 'Generate a page containing javascript',
        'requirement_type': 'content_match',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'invisible_ink': {
        'name': 'Invisible Ink',
        'description': 'Generate a page with white background and text',
        'requirement_type': 'style_match',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'digestive_mistro': {
        'name': 'Digestive Mistro',
        'description': 'Generate a page with "poop" in the prompt',
        'requirement_type': 'prompt_match',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'buffed_generation': {
        'name': 'Buffed Generation',
        'description': 'Generate a page while having an active effect. Reward: Ability to have an extra active consumable at a time',
        'requirement_type': 'buffed_generation',
        'requirement_count': 1,
        'reward_type': 'max_consumables', 
        'reward_amount': 1
    },
    'hoarder': {
        'name': 'Hoarder',
        'description': 'Have 50 trinkets at one time',
        'requirement_type': 'trinket_count',
        'requirement_count': 50,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'celebrity': {
        'name': 'Celebrity',
        'description': 'Generate a page that gets 25 views',
        'requirement_type': 'page_views',
        'requirement_count': 25,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'paparazzi': {
        'name': 'Paparazzi',
        'description': 'Generate a page with 4 images',
        'requirement_type': 'image_count',
        'requirement_count': 4,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'meme_lord': {
        'name': 'Meme Lord',
        'description': 'Generate a page containing "Rick Roll" or "Never Gonna Give You Up"',
        'requirement_type': 'content_match',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'night_owl': {
        'name': 'Night Owl',
        'description': 'Generate a page between 2 AM and 4 AM EST',
        'requirement_type': 'time_generation',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'perfectionist': {
        'name': 'Perfectionist',
        'description': 'Obtain an item with 100 quality. Reward: Minimum quality of items increased to 50',
        'requirement_type': 'perfect_quality',
        'requirement_count': 1,
        'reward_type': 'min_quality',
        'reward_amount': 50
    },
    'burger_beholder': {
        'name': 'Burger Beholder',
        'description': 'Generate 250 pages and complete half of available achievements. Reward: Allow you to harness the power of the Everything Burger',
        'requirement_type': 'complex',
        'requirement_count': 1,
        'reward_type': 'burger_power',
        'reward_amount': 1
    },
    'bug_hunter': {
        'name': 'Bug Hunter',
        'description': 'Generate a page containing "error" or "bug"',
        'requirement_type': 'content_match',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'mr_ocd': {
        'name': 'Mr OCD',
        'description': 'Generate a page with a list element',
        'requirement_type': 'html_element',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'poop_wizard': {
        'name': 'POOP WIZARD',
        'description': 'Generate a page containing "poop" and "wizard" without using either in the prompt',
        'requirement_type': 'special_content',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'fork_in_the_road': {
        'name': 'Fork in the Road',
        'description': 'Have someone else iterate on one of your pages for the first time.',
        'requirement_type': 'page_iterated_by_other',
        'requirement_count': 1,
        'reward_type': 'none',
        'reward_amount': 0
    },
    'branching_out': {
        'name': 'Branching Out',
        'description': 'Iterate on 5 different pages.',
        'requirement_type': 'iterations_created',
        'requirement_count': 5,
        'reward_type': 'none',
        'reward_amount': 0
    }
}

DAILY_QUEST_TYPES = {
    'post_comments': {
        'name': 'Comment Master',
        'description': 'Post {count} comments on pages',
        'min_count': 1,
        'max_count': 5,
        'base_crumbs': 50,
        'base_xp': 25
    },
    'send_votes': {
        'name': 'Voting Spree',
        'description': 'Vote on {count} pages',
        'min_count': 3,
        'max_count': 10,
        'base_crumbs': 30,
        'base_xp': 15
    },
    'quality_items': {
        'name': 'Quality Hunter',
        'description': 'Receive {count} items with quality above {threshold}',
        'min_count': 1,
        'max_count': 3,
        'base_crumbs': 100,
        'base_xp': 50,
        'threshold': 75
    },
    'trade_ups': {
        'name': 'Trade Master',
        'description': 'Complete {count} successful trade-ups',
        'min_count': 1,
        'max_count': 3,
        'base_crumbs': 150,
        'base_xp': 75
    },
    'generate_pages': {
        'name': 'Page Creator',
        'description': 'Generate {count} new pages',
        'min_count': 1,
        'max_count': 5,
        'base_crumbs': 80,
        'base_xp': 40
    },
    'use_consumables': {
        'name': 'Item Consumer',
        'description': 'Use {count} consumable items',
        'min_count': 1,
        'max_count': 3,
        'base_crumbs': 60,
        'base_xp': 30
    },
    'view_pages': {
        'name': 'Page Explorer',
        'description': 'View {count} different pages',
        'min_count': 5,
        'max_count': 15,
        'base_crumbs': 40,
        'base_xp': 20
    },
    'list_items': {
        'name': 'Merchant',
        'description': 'List {count} items for sale',
        'min_count': 1,
        'max_count': 3,
        'base_crumbs': 70,
        'base_xp': 35
    },
    'iterate_pages': {
        'name': 'Page Iterater',
        'description': 'Iterate on {count} public pages',
        'min_count': 1,
        'max_count': 2,
        'base_crumbs': 50,
        'base_xp': 25
    },
    'save_pages': {
        'name': 'Page Saver',
        'description': 'Save {count} pages',
        'min_count': 1,
        'max_count': 5,
        'base_crumbs': 40,
        'base_xp': 20
    }
}

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    # Password reset fields
    reset_token = db.Column(db.String(36), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

    # Featured pages for profile display (max 3)
    featured_page_1_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    featured_page_2_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    featured_page_3_id = db.Column(db.Integer, db.ForeignKey('pages.id'))

    featured_page_1 = relationship('Page', foreign_keys=[featured_page_1_id])
    featured_page_2 = relationship('Page', foreign_keys=[featured_page_2_id])
    featured_page_3 = relationship('Page', foreign_keys=[featured_page_3_id])
    # Profile fields
    banner_url = db.Column(db.String(500))
    profile_picture_url = db.Column(db.String(500))
    bio = db.Column(db.Text)

    # Usage metrics
    pages_generated = db.Column(db.Integer, default=0)

    # Relationships
    pages = relationship('Page',
                        foreign_keys='Page.creator_id',
                        back_populates='creator')
    comments = relationship('Comment', back_populates='author')
    votes = relationship('Vote', back_populates='user')
    inventory = relationship('Item', back_populates='user')
    achievements = relationship('UserAchievement', back_populates='user')
    max_active_effects = db.Column(db.Integer, default=1)

    # Crumb tracking
    current_crumbs = db.Column(db.Integer, default=0, nullable=False)
    lifetime_crumbs = db.Column(db.Integer, default=0, nullable=False)

    level = db.Column(db.Integer, default=1, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    
    def add_xp(self, amount):
        self.xp += amount
        
        while self.xp >= int(100 * (1.2 ** (self.level - 1))) and self.level < 100:
            level_requirement = int(100 * (1.2 ** (self.level - 1)))
            self.xp -= level_requirement
            self.level += 1
            self.add_crumbs(self.level * 25)

    def add_crumbs(self, amount):
        if self.current_crumbs is None:
            self.current_crumbs = 0
        if self.lifetime_crumbs is None:
            self.lifetime_crumbs = 0
        self.current_crumbs += amount
        self.lifetime_crumbs += amount
        db.session.commit()
        logger.info(f"Adding {amount} crumbs to user {self.id}")
        
    def remove_crumbs(self, amount):
        if self.current_crumbs is None:
            self.current_crumbs = 0
        self.current_crumbs = max(0, self.current_crumbs - amount)
        db.session.commit()
        logger.info(f"Removing {amount} crumbs from user {self.id}")
        
    def get_crumb_balance(self) -> dict:
        return {
            'current': self.current_crumbs,
            'lifetime': self.lifetime_crumbs
        }

    # Add this line to create the relationship
    daily_quests = relationship('DailyQuest', back_populates='user')

class Page(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    html_content = db.Column(db.Text, nullable=False)
    thumbnail_url = db.Column(db.String(500))
    prompt = db.Column(db.Text)  # Store the original prompt used to generate

    # Metrics and status
    visibility = db.Column(db.String(20), default='public')  # Values: 'public', 'unlisted', 'private'
    view_count = db.Column(db.Integer, default=0)
    upvote_count = db.Column(db.Integer, default=0)
    downvote_count = db.Column(db.Integer, default=0)
    score = db.Column(db.Float, default=0.0)  # Calculated field for ranking

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Tags for categorization and search
    tags = db.Column(db.String(500))  # Comma-separated tags
    current_iteration_id = db.Column(db.Integer, nullable=True)

    # Relationships
    creator = relationship('User',
                         foreign_keys=[creator_id],
                         back_populates='pages')
    comments = relationship('Comment', back_populates='page', cascade='all, delete-orphan')
    votes = relationship('Vote', back_populates='page', cascade='all, delete-orphan')

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Foreign Keys
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)  # For nested comments

    # Relationships
    page = relationship('Page', back_populates='comments')
    author = relationship('User', back_populates='comments')
    replies = relationship('Comment', backref='parent', remote_side=[id])

class Vote(db.Model):
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    is_upvote = db.Column(db.Boolean, nullable=False)  # True for upvote, False for downvote
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Keys
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    page = relationship('Page', back_populates='votes')
    user = relationship('User', back_populates='votes')

class PageIteration(db.Model):
    __tablename__ = 'page_iterations'

    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=False)
    parent_iteration_id = db.Column(db.Integer, db.ForeignKey('page_iterations.id'), nullable=True)
    html_content = db.Column(db.Text, nullable=False)
    prompt = db.Column(db.Text, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    iteration_number = db.Column(db.Integer, nullable=False, default=0)

    page = db.relationship('Page', foreign_keys=[page_id], backref=db.backref('iterations', cascade='all, delete-orphan'))
    author = db.relationship('User', backref='iterations')
    parent = db.relationship('PageIteration', remote_side=[id], backref='children')


class WatcherVerdict(db.Model):
    __tablename__ = 'watcher_verdicts'

    id = db.Column(db.Integer, primary_key=True)
    iteration_id = db.Column(db.Integer, db.ForeignKey('page_iterations.id'), nullable=False, unique=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    points_json = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    iteration = db.relationship('PageIteration', backref=db.backref('watcher_verdict', uselist=False, cascade='all, delete-orphan'))
    page = db.relationship('Page', backref=db.backref('watcher_verdicts', cascade='all, delete-orphan'))

    @property
    def points(self):
        return json.loads(self.points_json)

    @points.setter
    def points(self, value):
        self.points_json = json.dumps(value)


class DailyQuest(db.Model):
    __tablename__ = 'daily_quests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    quest_type = db.Column(db.String(50), nullable=False)  # e.g. 'create_pages', 'vote', 'comment'
    target_amount = db.Column(db.Integer, nullable=False)  # Amount needed to complete
    current_progress = db.Column(db.Integer, default=0)
    reward_type = db.Column(db.String(50), nullable=False)  # e.g. 'crumbs', 'xp'
    reward_amount = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='daily_quests')

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def update_progress(self, amount=1):
        if not self.completed and not self.is_expired():
            self.current_progress = min(self.current_progress + amount, self.target_amount)
            if self.current_progress >= self.target_amount:
                self.completed = True
                # Give rewards
                if self.reward_type == 'both':
                    # Give crumbs and XP
                    self.user.current_crumbs += self.reward_amount
                    self.user.lifetime_crumbs += self.reward_amount
                    self.user.add_xp(self.reward_amount // 2)
                elif self.reward_type == 'crumbs':
                    self.user.current_crumbs += self.reward_amount
                    self.user.lifetime_crumbs += self.reward_amount
                elif self.reward_type == 'xp':
                    self.user.add_xp(self.reward_amount)
                return True
        return False


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    rarity = db.Column(db.Enum(ItemRarity), nullable=False)
    type = db.Column(db.Enum(ItemType), nullable=False)
    icon_url = db.Column(db.String(500))
    effect_type = db.Column(db.String(50))
    effect_value = db.Column(db.String(100))
    effect_duration = db.Column(db.Integer)
    tradeable = db.Column(db.Boolean, default=True)
    infinite_uses = db.Column(db.Boolean, default=False)
    quality = db.Column(db.Integer, nullable=False)
    crumb_value = db.Column(db.Integer, default=0)
    for_sale = db.Column(Boolean, default=False)
    sale_price = db.Column(Integer, default=0)
    
    # Inventory tracking fields
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    quantity = db.Column(db.Integer, default=1)
    uses_remaining = db.Column(db.Integer)
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='inventory')

    def get_icon_url(self):
        if self.type == ItemType.TRINKET:
            # Return rarity-based icon for trinkets
            return f"/static/icons/trinkets/{self.rarity.value}.png"
        else:
            # Return custom icon for consumables and artifacts
            return self.icon_url

    def use(self, user_id):
        if self.type != ItemType.CONSUMABLE:
            return False, "Only consumables can be used"
        
        if self.uses_remaining <= 0:
            return False, "No uses remaining"

        # Handle clear_boosts effect type first
        if self.effect_type == 'clear_boosts':
            self.clear_active_effects(user_id)
            success = True
            message = "Cleared all active effects"
        else:
            # Check for existing generation style effect
            if self.effect_type == 'generation_style':
                existing_style = db.session.query(ActiveEffect).filter(
                    ActiveEffect.user_id == user_id,
                    ActiveEffect.effect_type == 'generation_style',
                    ActiveEffect.expires_at > datetime.utcnow()
                ).first()
                if existing_style:
                    return False, "You already have a generation style active. Only one style can be active at a time."

            # Check active effects count for non-clearing items
            active_count = db.session.query(ActiveEffect).filter(
                ActiveEffect.user_id == user_id,
                ActiveEffect.expires_at > datetime.utcnow()
            ).count()
            
            user = db.session.query(User).get(user_id)
            if active_count >= user.max_active_effects:
                return False, f"Cannot have more than {user.max_active_effects} active effects"

            # Add new effect
            expires_at = datetime.utcnow() + timedelta(seconds=self.effect_duration)
            new_effect = ActiveEffect(
                user_id=user_id,
                effect_type=self.effect_type,
                effect_value=self.effect_value,
                expires_at=expires_at
            )
            db.session.add(new_effect)
            success = True
            message = f"Applied {self.name} effect"

        # Reduce uses and delete if depleted
        self.uses_remaining -= 1
        if self.uses_remaining <= 0:
            db.session.delete(self)
        
        db.session.commit()
        return success, message

    @staticmethod
    def clear_active_effects(user_id):
        db.session.query(ActiveEffect).filter(
            ActiveEffect.user_id == user_id,
            ActiveEffect.expires_at > datetime.utcnow()
        ).delete()
        db.session.commit()

    @staticmethod
    def get_active_effects(user_id):
        return db.session.query(ActiveEffect).filter(
            ActiveEffect.user_id == user_id,
            ActiveEffect.expires_at > datetime.utcnow()
        ).all()

class Achievement(db.Model):
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(500))
    requirement_type = db.Column(db.String(50))
    requirement_count = db.Column(db.Integer)
    reward_type = db.Column(db.String(50))
    reward_amount = db.Column(db.Integer)
    
    user_achievements = relationship('UserAchievement', back_populates='achievement')

class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'))
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

    user = relationship('User', back_populates='achievements')
    achievement = relationship('Achievement', back_populates='user_achievements')

class ActiveEffect(db.Model):
    __tablename__ = 'active_effects'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    effect_type = db.Column(db.String(50), nullable=False)
    effect_value = db.Column(db.String(100), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationship
    user = relationship('User', backref='active_effects')

def calculate_item_duration(base_duration: int, quality: int, rarity: ItemRarity, user_id: int) -> int:
    logger.info(f"Calculating item duration for user {user_id}")
    logger.info(f"Base duration: {base_duration}, Quality: {quality}, Rarity: {rarity}")
    
    # Rarity multipliers for duration
    rarity_multipliers = {
        ItemRarity.COMMON: 1.0,
        ItemRarity.RARE: 1.5,
        ItemRarity.EPIC: 2.0,
        ItemRarity.LEGENDARY: 2.5
    }
    
    # Check for Time Whisperer artifact
    logger.info("Checking for Time Whisperer artifact")
    has_time_whisperer = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name == "Time Whisperer"
    ).first() is not None
    
    # Calculate duration based on quality, rarity, and Time Whisperer if present
    duration = base_duration * (1 + (quality / 100)) * rarity_multipliers.get(rarity, 1.0)
    logger.info(f"Initial duration calculation: {duration}")
    
    if has_time_whisperer:
        logger.info("Time Whisperer artifact found, applying 1.5x multiplier")
        duration *= 1.5
        
    final_duration = int(duration)
    logger.info(f"Final calculated duration: {final_duration}")
    return final_duration

def get_available_rarities(user_id: int, item_type: ItemType) -> list:
    logger.info(f"Getting available rarities for user {user_id} and item type {item_type}")
    available = []
    for rarity in ItemRarity:
        if rarity != ItemRarity.MYTHICAL:
            # For artifacts, check if user owns any of this rarity
            if item_type == ItemType.ARTIFACT:
                owned = db.session.query(Item).filter(
                    Item.type == ItemType.ARTIFACT,
                    Item.rarity == rarity,
                    Item.user_id == user_id
                ).count()
                logger.info(f"User owns {owned} artifacts of rarity {rarity}")
                if owned == 0:
                    available.append(rarity)
            # For other types, always available
            else:
                available.append(rarity)
    logger.info(f"Available rarities: {available}")
    return available

def roll_item_type(user_id: int) -> ItemType:
    logger.info(f"Rolling item type for user {user_id}")
    # Check if user has all artifact rarities
    artifact_rarities = get_available_rarities(user_id, ItemType.ARTIFACT)
    if not artifact_rarities:
        logger.info("User has all artifact rarities, rolling only consumable or trinket")
        # If user has all artifacts, only roll consumable or trinket
        result = random.choices(
            [ItemType.CONSUMABLE, ItemType.TRINKET],
            weights=[0.5, 0.5]
        )[0]
        logger.info(f"Rolled item type: {result}")
        return result
    
    result = random.choices(
        list(TYPE_WEIGHTS.keys()),
        weights=list(TYPE_WEIGHTS.values())
    )[0]
    logger.info(f"Rolled item type: {result}")
    return result

def roll_rarity(user_id: int, item_type: ItemType) -> ItemRarity:
    logger.info(f"Rolling rarity for user {user_id} and item type {item_type}")
    available = get_available_rarities(user_id, item_type)
    
    if not available:
        logger.info("No rarities available for this type, trying different type")
        # If no rarities available for this type, try a different type
        new_type = roll_item_type(user_id)
        if new_type == item_type:  # Prevent infinite recursion
            logger.info("Preventing infinite recursion, returning COMMON rarity")
            return ItemRarity.COMMON
        return roll_rarity(user_id, new_type)
        
    # Check for Lucky Horseshoe artifact
    logger.info("Checking for Lucky Horseshoe artifact")
    has_lucky_horseshoe = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name == "Lucky Horseshoe"
    ).first() is not None
    
    # Get base weights
    weights = [RARITY_WEIGHTS[r] for r in available]
    logger.info(f"Base rarity weights: {weights}")
    
    # Apply Lucky Horseshoe effect if present
    if has_lucky_horseshoe:
        logger.info("Lucky Horseshoe found, increasing rare item weights by 50%")
        # Increase weights for rarer items by 50%
        for i, rarity in enumerate(available):
            if rarity != ItemRarity.COMMON:
                weights[i] *= 1.5
    
    # Normalize weights
    total = sum(weights)
    normalized = [w/total for w in weights]
    logger.info(f"Normalized weights: {normalized}")
    
    result = random.choices(available, weights=normalized)[0]
    logger.info(f"Rolled rarity: {result}")
    return result

def generate_trinket_details(prompt: str) -> tuple:
    logger.info("Generating trinket details")
    logger.info(f"Input prompt: {prompt}")
    system_prompt = """You are a trinket generator for a game. Generate a trinket name and description that is relevant to the input text you are given no matter how nonsensical, outlandish, or unconventional it may be in this exact format:
    
    NAME: [short 2-4 word name]
    DESCRIPTION: [1-2 sentence description of magical/mystical properties]
    
    Keep names concise and descriptions brief but evocative. NO MATTER WHAT INPUT TEXT YOU ARE GIVEN, YOU MUST RETURN A TRINKET NAME AND DESCRIPTION IN THE EXACT FORMAT SHOWN ABOVE."""
    
    result = complete(
        'summary',
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        top_p=0.25,
    )
    name = result.split("NAME: ")[1].split("\n")[0].strip()
    description = result.split("DESCRIPTION: ")[1].strip()
    
    logger.info(f"Generated trinket name: {name}")
    logger.info(f"Generated trinket description: {description}")
    
    return (name, description)

def roll_quality(user_id: int) -> int:
    # Check if user has perfectionist achievement which sets minimum quality to 50
    base_min = 50 if has_achievement(user_id, 'perfectionist') else 1
    quality = random.randint(base_min, 100)
    logger.info(f"Rolled quality: {quality}")
    return quality

# Define keywords that increase trinket value
VALUABLE_KEYWORDS = ['valuable', 'sought after', 'rare', 'precious']

def calculate_crumb_value(item: Item) -> int:
    if item.type == ItemType.ARTIFACT:
        return 0  # Artifacts are not tradeable

    base_value = 10  # Base value for consumables
    if item.type == ItemType.TRINKET:
        base_value = 15  # Trinkets are worth slightly more

    # Rarity multipliers
    rarity_multipliers = {
        ItemRarity.COMMON: 1.0,
        ItemRarity.RARE: 1.5,
        ItemRarity.EPIC: 2.0,
        ItemRarity.LEGENDARY: 2.5
    }
    
    # Calculate initial crumb value
    crumb_value = base_value * rarity_multipliers.get(item.rarity, 1.0) * (item.quality / 100)

    # Additional multiplier for trinkets with valuable keywords
    if item.type == ItemType.TRINKET:
        if any(keyword in item.description.lower() for keyword in VALUABLE_KEYWORDS):
            crumb_value *= 1.2  # Increase by 20% if description contains valuable keywords

    # Check if user has Dopamine Enhancer artifact
    if item.user_id:  # Only check if item is assigned to a user
        has_dopamine_enhancer = db.session.query(Item).filter(
            Item.user_id == item.user_id,
            Item.name == "Dopamine Enhancer"
        ).first() is not None
        
        if has_dopamine_enhancer:
            crumb_value *= 1.5  # Apply 50% increase from Dopamine Enhancer

    return int(crumb_value)

def assign_crumb_value_to_existing_items():
    items = db.session.query(Item).all()
    for item in items:
        if item.type == ItemType.ARTIFACT:
            item.crumb_value = 0
        else:
            item.crumb_value = calculate_crumb_value(item)
    db.session.commit()


def get_item_for_user(user_id: int, prompt: str = None) -> Item:
    logger.info(f"Getting item for user {user_id}")
    if prompt:
        logger.info(f"With prompt: {prompt}")
    
    if random.random() < 0.15:  
        logger.info("Rolling for fragment (15% chance)")
        has_fragment_achievement = db.session.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == 1,
            UserAchievement.completed == True
        ).first() is not None

        if has_achievement(user_id, 'collector'):
            logger.info("User has collector achievement, proceeding with fragment roll")
            available_fragments = ['bun', 'patty', 'ketchup', 'pickle', 'cheese']
            
            # Always check existing fragments to prevent duplicates
            existing_fragments = db.session.query(Item.effect_value).filter(
                Item.user_id == user_id,
                Item.effect_type == 'fragment'
            ).all()
            existing_fragments = [f[0] for f in existing_fragments]
            available_fragments = [f for f in available_fragments if f not in existing_fragments]
            
            logger.info(f"Available fragments: {available_fragments}")
            
            if available_fragments:  # Only proceed if there are available fragments
                fragment_type = random.choice(available_fragments)
                logger.info(f"Selected fragment type: {fragment_type}")
                fragment_key = f'{fragment_type}_fragment'
                
                fragment = Item(
                    name=ITEMS[fragment_key]['name'],
                    description=ITEMS[fragment_key]['description'],
                    type=ItemType.ARTIFACT,
                    rarity=ItemRarity.MYTHICAL,
                    effect_type='fragment',
                    effect_value=fragment_type,
                    quality=100,
                    user_id=user_id,
                    tradeable=False,
                    icon_url=f"/static/icons/artifacts/{fragment_type}_fragment.png"
                )
                
                db.session.add(fragment)
                db.session.commit()
                logger.info(f"Created new fragment: {fragment.name}")
                
                # Check if we can assemble a burger
                if check_and_assemble_burger(user_id):
                    logger.info("Burger assembly triggered")
                    return db.session.query(Item).filter(
                        Item.user_id == user_id,
                        Item.effect_type == 'burger'
                    ).first()
                    
                return fragment

    # Continue with normal item generation if no fragment was created
    logger.info("Proceeding with normal item generation")
    item_type = roll_item_type(user_id)
    rarity = roll_rarity(user_id, item_type)
    quality = 100 if item_type == ItemType.ARTIFACT else roll_quality(user_id)
    
    if item_type == ItemType.TRINKET:
        logger.info("Generating trinket")
        name, desc = generate_trinket_details(prompt)
        return Item(
            name=name,
            description=desc,
            type=item_type,
            rarity=rarity,
            quality=quality,
            user_id=user_id,
            icon_url=f"/static/icons/trinkets/{rarity.value}.png"
        )
        
    if item_type == ItemType.ARTIFACT:
        logger.info("Generating artifact")
        # Get all artifacts from ITEMS dictionary
        available_artifacts = {
            key: item for key, item in ITEMS.items() 
            if item['type'] == ItemType.ARTIFACT 
            and item.get('rarity') == rarity
        }
        
        # Filter out artifacts user already has
        owned_artifacts = db.session.query(Item.name).filter(
            Item.user_id == user_id,
            Item.type == ItemType.ARTIFACT
        ).all()
        owned_names = [item.name for item in owned_artifacts]
        
        available_artifacts = {
            key: item for key, item in available_artifacts.items()
            if item['name'] not in owned_names
        }
        
        logger.info(f"Available artifacts: {list(available_artifacts.keys())}")
        
        if available_artifacts:
            template = random.choice(list(available_artifacts.values()))
            logger.info(f"Selected artifact template: {template['name']}")
            return Item(
                name=template['name'],
                description=template['description'],
                type=template['type'],
                rarity=template['rarity'],
                quality=quality,
                effect_type=template.get('effect_type'),
                effect_value=template.get('effect_value'),
                user_id=user_id,
                tradeable=False,
                icon_url=f"/static/icons/artifacts/{template['name'].lower().replace(' ', '_')}.png"
            )
        # If no artifacts available, roll a different type
        logger.info("No artifacts available, rolling different type")
        return get_item_for_user(user_id, prompt)
    
    # For consumables, get template from ITEMS dictionary
    if item_type == ItemType.CONSUMABLE:
        logger.info("Generating consumable")
        consumables = {
            key: item for key, item in ITEMS.items() 
            if item['type'] == ItemType.CONSUMABLE
        }
        template = random.choice(list(consumables.values()))
        logger.info(f"Selected consumable template: {template['name']}")
        
        # Set uses based on rarity
        uses = {
            ItemRarity.COMMON: 1,
            ItemRarity.RARE: 2,
            ItemRarity.EPIC: 3,
            ItemRarity.LEGENDARY: 4
        }.get(rarity, 1)
        
        # Calculate duration based on quality and rarity
        base_duration = template.get('effect_duration', 0)
        adjusted_duration = calculate_item_duration(base_duration, quality, rarity, user_id)
        
        return Item(
            name=template['name'],
            description=template['description'],
            type=template['type'],
            rarity=rarity,
            quality=quality,
            effect_type=template.get('effect_type'),
            effect_value=template.get('effect_value'),
            effect_duration=adjusted_duration,
            uses_remaining=uses,
            user_id=user_id,
            icon_url=f"/static/icons/consumables/{template['name'].lower().replace(' ', '_')}.png"
        )
    
    # Should never reach here, but return a trinket as final fallback
    logger.warning("Reached fallback case, generating trinket")
    return get_item_for_user(user_id, prompt)

def update_achievement_progress(user_id: int, achievement_name: str, progress_amount: int) -> bool:
    logger.info(f"Updating achievement progress for user {user_id}, achievement {achievement_name}")
    
    # Verify achievement exists in dictionary
    if achievement_name not in ACHIEVEMENTS:
        logger.error(f"Invalid achievement name: {achievement_name}")
        return False
    
    achievement_template = ACHIEVEMENTS[achievement_name]

    # Check if user already has completed this achievement
    existing_achievement = db.session.query(UserAchievement).join(Achievement).filter(
        UserAchievement.user_id == user_id,
        Achievement.name == achievement_template['name'],
        UserAchievement.completed == True
    ).first()
    
    if existing_achievement:
        logger.info(f"User {user_id} already completed achievement {achievement_name}")
        return False

    # Get or create achievement record if it doesn't exist
    achievement = db.session.query(Achievement).filter(
        Achievement.name == achievement_template['name']
    ).first()
    
    if not achievement:
        achievement = Achievement(
            name=achievement_template['name'],
            description=achievement_template['description'],
            requirement_type=achievement_template['requirement_type'],
            requirement_count=achievement_template['requirement_count'],
            reward_type=achievement_template['reward_type'],
            reward_amount=achievement_template['reward_amount']
        )
        db.session.add(achievement)
        db.session.flush()
        logger.info(f"Created new achievement record for {achievement_name}")

    # Get or create user achievement progress
    user_achievement = db.session.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement.id
    ).first()
    
    if not user_achievement:
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            progress=0
        )
        db.session.add(user_achievement)
        logger.info(f"Created new achievement progress tracking for user {user_id}")

    # Update progress - Set directly instead of adding
    user_achievement.progress = progress_amount
    logger.info(f"Updated progress to {user_achievement.progress}/{achievement.requirement_count}")

    # Check if achievement is completed
    if user_achievement.progress >= achievement.requirement_count:
        user_achievement.completed = True
        user_achievement.completed_at = datetime.utcnow()
        logger.info(f"Achievement {achievement_name} completed for user {user_id}")
        db.session.commit()
        return True

    db.session.commit()
    return False

def grant_achievement(user_id: int, achievement_name: str) -> bool:
    logger.info(f"Attempting to grant achievement {achievement_name} to user {user_id}")
    
    # Verify achievement exists
    if achievement_name not in ACHIEVEMENTS:
        logger.error(f"Invalid achievement name: {achievement_name}")
        return False

    achievement = db.session.query(Achievement).filter(
        Achievement.name == ACHIEVEMENTS[achievement_name]['name']
    ).first()
    
    if not achievement:
        logger.error(f"Achievement {achievement_name} not found in database")
        return False

    # Check if user already has this achievement
    existing_achievement = db.session.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement.id,
        UserAchievement.completed == True
    ).first()
    
    if existing_achievement:
        logger.info(f"User {user_id} already has achievement {achievement_name}")
        return False

    # Create new completed achievement
    new_achievement = UserAchievement(
        user_id=user_id,
        achievement_id=achievement.id,
        progress=achievement.requirement_count,
        completed=True,
        completed_at=datetime.utcnow()
    )
    
    try:
        db.session.add(new_achievement)
        db.session.commit()
        logger.info(f"Successfully granted achievement {achievement_name} to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error granting achievement: {str(e)}")
        db.session.rollback()
        return False

def has_achievement(user_id: int, achievement_name: str) -> bool:
    logger.info(f"Checking if user {user_id} has achievement {achievement_name}")
    
    if achievement_name not in ACHIEVEMENTS:
        logger.error(f"Invalid achievement name: {achievement_name}")
        return False
        
    achievement_template = ACHIEVEMENTS[achievement_name]
    
    existing_achievement = db.session.query(UserAchievement).join(Achievement).filter(
        UserAchievement.user_id == user_id,
        Achievement.name == achievement_template['name'],
        UserAchievement.completed == True
    ).first()
    
    return existing_achievement is not None

def check_and_assemble_burger(user_id: int) -> bool:
    logger.info(f"Checking burger assembly for user {user_id}")
    
    # Get all burgers owned by user
    existing_burgers = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name.like("Everything Burger%"),
        Item.type == ItemType.ARTIFACT,
        Item.rarity == ItemRarity.MYTHICAL
    ).all()
    
    # Get all fragments owned by user
    fragments = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.effect_type == 'fragment',
        Item.rarity == ItemRarity.MYTHICAL,
        Item.type == ItemType.ARTIFACT
    ).all()
    
    # Get unique fragment types
    fragment_types = set(fragment.effect_value for fragment in fragments)
    required_fragments = {'bun', 'patty', 'ketchup', 'pickle', 'cheese'}
    
    # Handle multiple burgers first - keep highest level and delete others
    if len(existing_burgers) > 1:
        logger.info(f"Found {len(existing_burgers)} burgers, consolidating...")
        # Sort burgers by level (effect_value)
        sorted_burgers = sorted(existing_burgers, key=lambda x: int(x.effect_value))
        highest_burger = sorted_burgers[-1]
        
        # Delete all but the highest level burger
        for burger in sorted_burgers[:-1]:
            highest_burger.effect_value = int(highest_burger.effect_value) + int(burger.effect_value) + 1
            db.session.delete(burger)
            
        # Update highest burger's name and description
        highest_burger.name = f"Everything Burger +{highest_burger.effect_value}"
        highest_burger.description = f"{ITEMS['everything_burger']['description']} (Level {highest_burger.effect_value})"
        db.session.commit()
        existing_burgers = [highest_burger]
    
    # Check if we have all required fragments
    if len(fragments) >= len(required_fragments):
        logger.info("All fragments collected, assembling/upgrading burger")
        
        # Delete all fragments
        for fragment in fragments:
            db.session.delete(fragment)
        
        if existing_burgers:
            # Level up existing burger
            burger = existing_burgers[0]
            current_level = int(burger.effect_value)
            burger.effect_value = current_level + 1
            burger.name = f"Everything Burger +{current_level + 1}"
            burger.description = f"{ITEMS['everything_burger']['description']} (Level {current_level + 1})"
            logger.info(f"Leveled up Everything Burger to +{current_level + 1}")
        else:
            # Create the initial Everything Burger
            burger = Item(
                name=ITEMS['everything_burger']['name'],
                description=ITEMS['everything_burger']['description'],
                type=ItemType.ARTIFACT,
                rarity=ItemRarity.MYTHICAL,
                effect_type='burger',
                effect_value=0,
                quality=100,
                user_id=user_id,
                tradeable=False,
                icon_url="/static/icons/artifacts/everything_burger.png"
            )
            db.session.add(burger)
            
            # Grant the Chad Status achievement
            grant_achievement(user_id, 'chad_status')
        
        db.session.commit()
        logger.info("Everything Burger assembled/upgraded successfully")
        return True
        
    logger.info(f"Not all fragments collected. Have: {fragment_types}")
    return False
