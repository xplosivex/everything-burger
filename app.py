from gevent import monkey
monkey.patch_all()
from mistralai.client import Mistral
import os
import json
import math
import random
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
import gevent
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from sqlalchemy import func, text
import pytz

from model import (
    User, Page, Vote, Comment, db, get_item_for_user,
    calculate_item_duration, Achievement, UserAchievement, Item, ItemType,
    ItemRarity, ITEMS, ActiveEffect,
    ACHIEVEMENTS, update_achievement_progress, has_achievement,
    check_and_assemble_burger, calculate_shop_price, SHOP_ITEMS,
    DAILY_QUEST_TYPES, DailyQuest, PageIteration, WatcherVerdict
)
import uuid
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import re
import tempfile
from selenium import webdriver
import os
import time
from serpapi import GoogleSearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure request logging handler
request_logger = logging.getLogger('werkzeug')
request_logger.setLevel(logging.INFO)

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# All secrets and tunables are read from environment variables (or a .env
# file in the project root). Copy .env.example to .env and fill in your keys.
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Mistral AI API key (https://console.mistral.ai) -- REQUIRED
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# SerpAPI key for Google image/news/video/shopping search (https://serpapi.com) -- REQUIRED
SERP_API_KEY = os.environ.get("SERP_API_KEY", "")

# Model assignments -- tune these based on cost/quality tradeoffs
CONTENT_MODEL = os.environ.get("CONTENT_MODEL", "mistral-large-latest")    # Best writing quality
STRUCTURE_MODEL = os.environ.get("STRUCTURE_MODEL", "codestral-latest")    # Best at code/HTML generation
STYLING_MODEL = os.environ.get("STYLING_MODEL", "mistral-medium-latest")   # Good balance for styling task
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "mistral-small-latest")     # Lightweight, fine for summaries

# Email configuration (used for password reset + welcome emails)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_ENABLED = bool(SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD)

# Public base URL used in password reset links (e.g. https://yourdomain.com)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Stable secret key for sessions. Set a fixed value in .env so sessions
# survive restarts. Falls back to a random key (sessions reset on restart).
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))

def create_app():
    app = Flask(__name__)

    # Create instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    # Configure app
    app.secret_key = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Add connection pool settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 30,  # Maximum number of persistent connections
        'max_overflow': 10,  # Maximum number of connections that can be created beyond pool_size
        'pool_timeout': 30,  # Seconds to wait before giving up on getting a connection
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
        'pool_pre_ping': True  # Enable connection health checks
    }

    app.permanent_session_lifetime = timedelta(days=1)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    # Ensure all tables are created
    with app.app_context():
        db.create_all()

    return app

# Create the application instance
app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent', transport='websocket')

@app.errorhandler(429)
def ratelimit_handler(e):
    flash_message("You're moving a little fast — try again in a moment.", "error")
    return redirect(request.referrer or url_for('dashboard'))

def send_reset_email(email, token):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Everything Burger Password Reset Request"

    body = f"""
    To reset your password, click the following link:
    {BASE_URL}/reset_password/{token}

    This link will expire in 1 hour.
    """

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_welcome_email(email, username):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Welcome to Everything Burger!"

    body = f"""
    Hi {username},

    Welcome to Everything Burger! It's the burger that does everything.
    If you can dream it, we can generate it.

    We hope you enjoy your time here.
    Thanks,
    The Everything Burger Creator.
    """

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash_message('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def find_insertion_point(soup):
    """Find an appropriate place to insert new content based on existing structure and styling"""
    logger.info("Finding insertion point for new content")
    try:
        main_content = soup.find('main') or soup.find('body')
        if not main_content:
            logger.info("No main or body tag found")
            return None
            
        # Look for natural break points
        potential_points = main_content.find_all(['div', 'section', 'article', 'p'], recursive=False)
        
        if not potential_points:
            logger.info("No potential insertion points found, using main content")
            return main_content
            
        # Try to find a point that's roughly 1/3 to 2/3 through the content
        target_index = len(potential_points) // 2
        start_index = max(0, target_index - 1)
        end_index = min(len(potential_points), target_index + 2)
        
        logger.info(f"Analyzing {end_index - start_index} potential insertion points")
        
        # Look for good break points within our target range
        for i in range(start_index, end_index):
            point = potential_points[i]
            
            # Prefer points after paragraphs or sections
            if point.name in ['p', 'section', 'article']:
                logger.info(f"Found ideal insertion point after {point.name}")
                return point
                
            # Check if point has similar styling to our theme
            if point.get('class'):
                classes = point.get('class', [])
                if isinstance(classes, str):
                    classes = classes.split()
                    
                # Look for common content division classes
                content_markers = ['container', 'section', 'content', 'wrapper']
                if any(marker in ' '.join(classes).lower() for marker in content_markers):
                    logger.info(f"Found styled insertion point with classes: {classes}")
                    return point
        
        # If no ideal point found, use the middle point
        logger.info("Using middle point as insertion point")
        return potential_points[target_index]
        
    except Exception as e:
        logger.error(f"Error finding insertion point: {str(e)}")
        # Fallback to main content or body
        return soup.find('main') or soup.find('body')

def generate_section_title(content_type, soup, search_query):
    """Generate contextual section titles based on content and existing headings"""
    logger.info(f"Generating section title for {content_type} content")
    try:
        # Ensure search_query is a string
        if not isinstance(search_query, str):
            search_query = str(search_query)
        
        existing_headings = [h.get_text().lower() for h in soup.find_all(['h1', 'h2', 'h3'])]
        base_text = search_query.lower()
        
        logger.info(f"Found {len(existing_headings)} existing headings")
        
        # Default titles if something goes wrong
        default_titles = {
            'news': "Related News",
            'videos': "Related Videos",
            'shopping': "Related Products"
        }
        
        title_patterns = {
            'news': [
                "Latest Updates on {topic}",
                "What's New in {topic}",
                "Trending {topic} News",
                "{topic} Headlines",
                "Recent Developments in {topic}",
                "Breaking {topic} Stories"
            ],
            'videos': [
                "Watch More About {topic}",
                "{topic} in Action",
                "Featured {topic} Videos",
                "Visual Guide to {topic}",
                "Explore {topic}",
                "{topic} Highlights"
            ],
            'shopping': [
                "Related {topic} Products",
                "Recommended {topic} Items",
                "Popular {topic} Picks",
                "Essential {topic} Gear",
                "Top {topic} Selections",
                "{topic} Must-Haves"
            ]
        }
        
        # Clean up the topic
        words = base_text.split()
        if not words:
            logger.info("No words found in search query, using default title")
            return default_titles[content_type]
            
        topic = ' '.join(word.capitalize() for word in words[:3])
        logger.info(f"Using topic: {topic}")
        
        # Select a random pattern that doesn't closely match existing headings
        patterns = title_patterns.get(content_type, [])
        if not patterns:
            logger.info("No patterns found for content type, using default title")
            return default_titles[content_type]
            
        random.shuffle(patterns)
        
        for pattern in patterns:
            title = pattern.format(topic=topic)
            if not any(title.lower() in heading or heading in title.lower() 
                      for heading in existing_headings):
                logger.info(f"Generated unique title: {title}")
                return title
        
        # Fallback to a simple title if all patterns are too similar
        fallback_title = f"{topic} {content_type.capitalize()}"
        logger.info(f"Using fallback title: {fallback_title}")
        return fallback_title
        
    except Exception as e:
        logger.error(f"Error generating section title: {str(e)}")
        return default_titles.get(content_type, "Related Content")

def create_complex_calculation(num):
    operations = [
        # Addition-based combinations
        lambda x: f"({x//3} + {x//3} + {x-(2*(x//3))})",
        lambda x: f"({x//4} + {x//4} + {x//4} + {x-(3*(x//4))})",
        lambda x: f"({x//5} + {x//5} + {x//5} + {x//5} + {x-(4*(x//5))})",
        
        # Multiplication with division
        lambda x: f"({x*6} Ã· 2 Ã· 3)",
        lambda x: f"({x*12} Ã· 3 Ã· 4)",
        lambda x: f"({x*8} Ã· 2 Ã· 4)",
        lambda x: f"({x*15} Ã· 3 Ã· 5)",
        
        # Powers and roots combined
        lambda x: f"(âˆš{x*x*4} Ã· 2)" if x <= 15 else f"({x-3} + 2 + 1)",
        lambda x: f"(2^{int(math.log2(x))} + {x - 2**int(math.log2(x))})",
        lambda x: f"(3^{int(math.log(x,3))} + {x - 3**int(math.log(x,3))})",
        
        # Mixed operations
        lambda x: f"(({x*3} Ã· 2) + ({x//2}))",
        lambda x: f"({x//5} Ã— 4 + {x - 4*(x//5)})",
        lambda x: f"({x*2} Ã· 4 + {x//2} Ã— 2)",
        lambda x: f"({x//3} Ã— 6 - {x//2})",
        
        # Nested operations
        lambda x: f"((({x*2} Ã· 2) Ã— 3) Ã· 3)",
        lambda x: f"(âˆš{(x//2)*2 * (x//2)*2})" if x % 2 == 0 else f"({x-2} + 1 + 1)",
        lambda x: f"((({x*4} Ã· 4) Ã— 2) Ã· 2)",
        lambda x: f"((({x//3} Ã— 6) Ã· 2) Ã— 1)",
        
        # Complex combinations
        lambda x: f"({x//6} Ã— 3 + {x//3} Ã— 2 + {x - (x//6)*3 - (x//3)*2})",
        lambda x: f"((âˆš{(x//3)*(x//3)} Ã— 3) + {x - (x//3)*3})" if x > 9 else f"({x-1} + 1)",
        lambda x: f"({x//8} Ã— 4 + {x//4} Ã— 2 + {x - (x//8)*4 - (x//4)*2})",
        lambda x: f"({x//2} Ã— 3 - {x//3} Ã— 2 + {x//6})",
        
        # Factorial-based (for small numbers)
        lambda x: f"(6 Ã· 2 Ã— {x})" if x <= 10 else f"({x-1} + 1)",
        lambda x: f"(24 Ã· 6 Ã— {x//4})" if x <= 20 else f"({x-2} + 2)",
        
        # Trigonometric (for variety)
        lambda x: f"(sin(90Â°) Ã— {x})",
        lambda x: f"(cos(0Â°) Ã— {x})"
    ]
    # Choose a random operation
    operation = random.choice(operations)
    return operation(num)

generated_content = {}

# ============================================================
# HTML GENERATION PIPELINE (merged from optimized_generation.py)
# ============================================================

# ---------------------------------------------------------------------------
# CONTENT BLOCK DEFINITIONS
# ---------------------------------------------------------------------------
#
# Three tiers:
#
#   STAPLE  — generic, plain building blocks (paragraph, list, table, etc.)
#             Can appear MULTIPLE TIMES in a single palette. High weight.
#             These form the connective tissue of every page.
#
#   COMMON  — flavorful but not wild. Appear at most ONCE per palette.
#             Medium weight. The reliable "interesting" blocks.
#
#   EXOTIC  — rare, highly specific, weird. Appear at most ONCE per palette.
#             Low weight. These are the "screenshot and send to a friend" blocks.
#
# Every block has:
#   prompt    — the text injected into the system prompt
#   category  — for cross-category diversity guarantees
#   weight    — selection probability (higher = more likely)
#   tier      — 'staple' | 'common' | 'exotic'
# ---------------------------------------------------------------------------

# These ALWAYS appear in the prompt -- every page needs them
CORE_BLOCKS = {
    'title': {
        'prompt': 'TITLE: [funny, dramatic, or absurd page title]',
    },
    'subtitle': {
        'prompt': 'SUBTITLE: [punchy one-liner or tagline]',
    },
    'image': {
        'prompt': (
            'IMAGE: [3-5 word description for image search]\n'
            'CAPTION: [funny or descriptive caption]\n'
            '(include 1-3 images placed naturally throughout the page)'
        ),
    },
}


# ======================================================================
# STAPLE BLOCKS — high weight, allow duplicates
# ======================================================================

STAPLE_BLOCKS = {
    'paragraph': {
        'prompt': (
            'PARAGRAPH: [a short, punchy paragraph about the topic -- '
            '2-3 sentences max. Entertaining, opinionated, or funny. NOT an essay.]'
        ),
        'category': 'structure',
        'weight': 10,
    },
    'section': {
        'prompt': (
            'SECTION: [heading]\n'
            '[1-2 SHORT paragraphs, 2-3 sentences each. Punchy. Not an essay.]'
        ),
        'category': 'structure',
        'weight': 10,
    },
    'list': {
        'prompt': (
            'LIST: [title]\n'
            '- [item 1]\n- [item 2]\n- [item 3]\n- [item 4]\n'
            '(3-6 short items, can be bullet points, to-dos, or any simple list)'
        ),
        'category': 'structure',
        'weight': 8,
    },
    'numbered_list': {
        'prompt': (
            'NUMBEREDLIST: [title]\n'
            '1. [item]\n2. [item]\n3. [item]\n'
            '(3-6 items, ordered by importance, steps, or ranking)'
        ),
        'category': 'structure',
        'weight': 7,
    },
    'table': {
        'prompt': (
            'TABLE: [title]\n'
            '| [col1] | [col2] | [col3] |\n'
            '| [data] | [data] | [data] |\n'
            '| [data] | [data] | [data] |\n'
            '(2-4 columns, 2-5 rows -- can be funny comparisons, fake data, etc.)'
        ),
        'category': 'structure',
        'weight': 6,
    },
    'heading_text': {
        'prompt': (
            'HEADING: [bold, punchy heading -- a statement, question, or exclamation]\n'
            'TEXT: [1-2 sentences that follow up on the heading]'
        ),
        'category': 'structure',
        'weight': 8,
    },
    'callout_box': {
        'prompt': (
            'CALLOUT: [emoji or label like "NOTE", "TIP", "DID YOU KNOW"]\n'
            'CONTENT: [1-2 sentences of highlighted information or commentary]'
        ),
        'category': 'structure',
        'weight': 7,
    },
    'divider_text': {
        'prompt': 'DIVIDER: [a funny or thematic one-liner to break up the page, like a subheading or interstitial joke]',
        'category': 'structure',
        'weight': 5,
    },
    'bold_statement': {
        'prompt': 'BOLD: [one big, confident, standalone sentence -- displayed large and centered, like a pull quote]',
        'category': 'structure',
        'weight': 6,
    },
    'caption_block': {
        'prompt': (
            'CAPTIONBLOCK: [a short blurb that reads like a photo caption or museum placard, '
            '1-2 sentences, slightly formal but funny]'
        ),
        'category': 'structure',
        'weight': 4,
    },
    'summary_box': {
        'prompt': (
            'SUMMARY: [title like "TL;DR" or "The Bottom Line"]\n'
            'CONTENT: [2-3 sentence summary -- opinionated, funny, or deliberately unhelpful]'
        ),
        'category': 'structure',
        'weight': 5,
    },
    'key_value': {
        'prompt': (
            'KEYVALUE: [title]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            'KEY: [label] -> VALUE: [data or funny answer]\n'
            '(3-5 key-value pairs, like a spec sheet or info card)'
        ),
        'category': 'structure',
        'weight': 5,
    },
    'blockquote': {
        'prompt': (
            'BLOCKQUOTE: [a notable, funny, or dramatic quote -- can be real-sounding or obviously fake]\n'
            'SOURCE: [attribution -- person, book, "ancient proverb", etc.]'
        ),
        'category': 'voice',
        'weight': 7,
    },
}

# ======================================================================
# COMMON BLOCKS — medium weight, no duplicates
# ======================================================================

COMMON_BLOCKS = {
    # --- VOICE & OPINION ---
    'funfact': {
        'prompt': 'FUNFACT: [one wild, surprising, or completely made-up "fact" -- stated with total confidence]',
        'category': 'voice',
        'weight': 6,
    },
    'quote': {
        'prompt': (
            'QUOTE: [absurd or hilariously specific quote]\n'
            'ATTRIBUTION: [funny fake source, e.g. "-- Dr. Gerald Hamsworth, Professor of Unnecessary Studies"]'
        ),
        'category': 'voice',
        'weight': 6,
    },
    'testimonial': {
        'prompt': (
            'TESTIMONIAL: [fake testimonial quote from a fake person]\n'
            'AUTHOR: [fake name and absurd title, e.g. "Brenda K., Certified Soup Whisperer"]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'debate': {
        'prompt': (
            'DEBATE: [hot take or controversial opinion stated as fact]\n'
            'COUNTERPOINT: [opposing view, equally confident]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'hot_take': {
        'prompt': 'HOTTAKE: [a single bold, provocative sentence about the topic that sounds like a viral tweet]',
        'category': 'voice',
        'weight': 6,
    },
    'unpopular_opinion': {
        'prompt': (
            'UNPOPULAROPINION: [an opinion about the topic framed as deeply controversial]\n'
            'DEFENSE: [1-2 sentence surprisingly compelling defense of it]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'overheard': {
        'prompt': (
            'OVERHEARD: [a snippet of fake conversation between two people about the topic, '
            '3-4 lines of dialogue, funny or absurd]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'review': {
        'prompt': (
            'REVIEW: [fake 1-5 star review of the topic as if it were a product or experience]\n'
            'STARS: [number 1-5]\n'
            'REVIEWER: [fake name and detail like "Verified Purchaser" or "Local Guide"]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'complaint': {
        'prompt': (
            'COMPLAINT: [fake angry customer complaint about the topic, '
            '2-3 sentences of escalating outrage]\n'
            'SIGNED: [fake name with petty title, e.g. "Karen M., Lifelong Taxpayer"]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'confession': {
        'prompt': (
            'CONFESSION: [a fake anonymous confession related to the topic, '
            'written like a late-night internet post -- funny or oddly specific]'
        ),
        'category': 'voice',
        'weight': 4,
    },
    'rant': {
        'prompt': (
            'RANT: [a 2-3 sentence passionate mini-rant about some aspect of the topic, '
            'getting increasingly unhinged by the last sentence]'
        ),
        'category': 'voice',
        'weight': 5,
    },
    'mic_drop': {
        'prompt': 'MICDROP: [one devastating, conversation-ending sentence about the topic -- stated with absolute finality]',
        'category': 'voice',
        'weight': 4,
    },

    # --- LISTS & RANKINGS ---
    'ranking': {
        'prompt': (
            'RANKING: [title of the ranking]\n'
            '1. [item] -- [one-line hot take]\n'
            '2. [item] -- [one-line hot take]\n'
            '3. [item] -- [one-line hot take]\n'
            '(3-7 items max)'
        ),
        'category': 'list',
        'weight': 6,
    },
    'tips': {
        'prompt': (
            'TIPS: [title]\n'
            '- [short tip 1]\n- [short tip 2]\n- [short tip 3]\n'
            '(3-5 tips, each one line)'
        ),
        'category': 'list',
        'weight': 6,
    },
    'stats': {
        'prompt': (
            'STATS: [title]\n'
            '- [made-up statistic with fake percentage]\n'
            '- [another fake stat]\n- [another fake stat]\n'
            '(2-4 stats)'
        ),
        'category': 'list',
        'weight': 5,
    },
    'tier_list': {
        'prompt': (
            'TIERLIST: [title -- what are we ranking?]\n'
            'S: [item]\nA: [item]\nB: [item]\nC: [item]\nF: [item]\n'
            '(one item per tier, with a 2-5 word justification each)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'pros_cons': {
        'prompt': (
            'PROSCONS: [thing being evaluated]\n'
            'PRO: [genuine-sounding positive]\nPRO: [another]\n'
            'CON: [funny or absurd negative]\nCON: [another]\n'
            'VERDICT: [one-line final judgment]'
        ),
        'category': 'list',
        'weight': 5,
    },
    'checklist': {
        'prompt': (
            'CHECKLIST: [title -- a funny "are you ready" or "do you qualify" checklist]\n'
            '- [ ] [item 1]\n- [ ] [item 2]\n- [ ] [item 3]\n'
            '- [x] [item 4 -- pre-checked for comedic effect]\n'
            '(4-6 items)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'starter_pack': {
        'prompt': (
            'STARTERPACK: [title -- "[Topic] Starter Pack"]\n'
            '- [item 1]\n- [item 2]\n- [item 3]\n- [item 4]\n- [item 5]\n'
            '(5-7 stereotypical items, funny and specific)'
        ),
        'category': 'list',
        'weight': 4,
    },
    'do_dont': {
        'prompt': (
            'DODONT: [title]\n'
            'DO: [good advice or funny instruction]\n'
            'DONT: [bad advice or absurd prohibition]\n'
            'DO: [another]\nDONT: [another]\n'
            '(2-4 pairs)'
        ),
        'category': 'list',
        'weight': 5,
    },
    'superlatives': {
        'prompt': (
            'SUPERLATIVES: [title -- "The [Topic] Awards"]\n'
            'MOST LIKELY TO: [item] -- [reason]\n'
            'BEST DRESSED: [item] -- [reason]\n'
            'LEAST LIKELY TO SURVIVE: [item] -- [reason]\n'
            '(3-5 funny superlative categories with winners)'
        ),
        'category': 'list',
        'weight': 4,
    },

    # --- DATA & COMPARISON ---
    'comparison': {
        'prompt': (
            'COMPARISON: [thing A] vs [thing B]\n'
            '[2-3 sentences comparing them in a funny or unexpected way]'
        ),
        'category': 'data',
        'weight': 5,
    },
    'timeline': {
        'prompt': (
            'TIMELINE: [title]\n'
            '- [year/date]: [event -- can be absurd]\n'
            '- [year/date]: [event]\n- [year/date]: [event]\n'
            '(3-5 entries)'
        ),
        'category': 'data',
        'weight': 5,
    },
    'poll': {
        'prompt': (
            'POLL: [funny poll question]\n'
            'OPTION: [answer 1]\nOPTION: [answer 2]\nOPTION: [answer 3]\n'
            '(2-4 options)'
        ),
        'category': 'data',
        'weight': 5,
    },
    'scale': {
        'prompt': (
            'SCALE: [what are we measuring? e.g. "How cursed is this?"]\n'
            '1: [label for low end]\n5: [label for middle]\n10: [label for high end]\n'
            'VERDICT: [where the topic lands, with a number and one-line reason]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'matchup': {
        'prompt': (
            'MATCHUP: [thing A] vs [thing B] -- FIGHT!\n'
            'ROUND1: [category] -- Winner: [A or B] -- [why]\n'
            'ROUND2: [category] -- Winner: [A or B] -- [why]\n'
            'ROUND3: [category] -- Winner: [A or B] -- [why]\n'
            'CHAMPION: [winner and trash-talk victory line]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'spectrum': {
        'prompt': (
            'SPECTRUM: [what dimension?]\n'
            'LEFT: [extreme 1]\nRIGHT: [extreme 2]\n'
            'ITEM: [thing] -- [where and why]\n'
            'ITEM: [thing] -- [where and why]\n'
            'ITEM: [thing] -- [where and why]\n'
            '(3-5 items placed on the spectrum)'
        ),
        'category': 'data',
        'weight': 3,
    },
    'flowchart': {
        'prompt': (
            'FLOWCHART: [title -- a decision tree or process]\n'
            'START: [question or starting point]\n'
            'IF YES: [outcome or next question]\n'
            'IF NO: [outcome or next question]\n'
            'RESULT: [funny final outcome]\n'
            '(a simple 3-5 step flowchart, can branch)'
        ),
        'category': 'data',
        'weight': 4,
    },
    'before_after': {
        'prompt': (
            'BEFOREAFTER: [title -- what changed?]\n'
            'BEFORE: [description of the "before" state, 1-2 sentences]\n'
            'AFTER: [description of the "after" state, 1-2 sentences]\n'
            'VERDICT: [was this an improvement? one-line take]'
        ),
        'category': 'data',
        'weight': 4,
    },
    'scoreboard': {
        'prompt': (
            'SCOREBOARD: [title -- what competition?]\n'
            '1ST: [item] -- [score or metric]\n'
            '2ND: [item] -- [score]\n'
            '3RD: [item] -- [score]\n'
            'LAST: [item] -- [score, hilariously low or absurd]'
        ),
        'category': 'data',
        'weight': 4,
    },

    # --- ALERTS & CALLOUTS ---
    'warning': {
        'prompt': 'WARNING: [fake warning box text -- dramatic, over-the-top, or weirdly specific]',
        'category': 'callout',
        'weight': 6,
    },
    'breaking': {
        'prompt': 'BREAKING: [fake breaking news headline -- dramatic and absurd]',
        'category': 'callout',
        'weight': 5,
    },
    'ad': {
        'prompt': 'AD: [fake advertisement for a ridiculous product or service related to the topic]',
        'category': 'callout',
        'weight': 5,
    },
    'sidebar': {
        'prompt': 'SIDEBAR: [interesting tangent, weird aside, or bonus fact]',
        'category': 'callout',
        'weight': 5,
    },
    'disclaimer': {
        'prompt': (
            'DISCLAIMER: [hilariously over-specific legal disclaimer related to the topic, '
            'written in fake legalese, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'error_message': {
        'prompt': (
            'ERROR: [fake error message or 404 screen related to the topic, '
            'e.g. "ERROR 418: Too much sauce detected"]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'notification': {
        'prompt': (
            'NOTIFICATION: [fake phone/app notification related to the topic, '
            'e.g. "DUOLINGO: You forgot to practice [topic]. We know where you live."]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'news_ticker': {
        'prompt': (
            'TICKER: [3-4 fake scrolling news headlines related to the topic, '
            'separated by " | ", each one absurd and punchy]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'loading_screen': {
        'prompt': (
            'LOADING: [fake loading/progress message related to the topic, '
            'e.g. "Downloading more opinions... 67%%" or "Buffering hot takes..."]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'psa': {
        'prompt': (
            'PSA: [a fake public service announcement related to the topic, '
            'overly serious tone about something trivial, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'update_banner': {
        'prompt': (
            'UPDATE: [a fake "EDIT" or "UPDATE" notice like you see on blog posts, '
            'e.g. "UPDATE (3:47 AM): We have been informed that [absurd correction]"]'
        ),
        'category': 'callout',
        'weight': 4,
    },
    'spoiler': {
        'prompt': (
            'SPOILER: [title -- what is being spoiled]\n'
            'CONTENT: [hidden content that is funny, anticlimactic, or absurd when revealed]'
        ),
        'category': 'callout',
        'weight': 4,
    },

    # --- INTERACTIVE ---
    'secret': {
        'prompt': (
            'SECRET: [title for expandable section, e.g. "Click to reveal the truth"]\n'
            'REVEAL: [hidden content -- funny, surprising, or anticlimactic]'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'quiz': {
        'prompt': (
            'QUIZ: [funny quiz question about the topic]\n'
            'A: [wrong answer]\nB: [wrong answer]\n'
            'C: [correct or funniest answer]\nD: [absurd answer]\n'
            'ANSWER: [letter and a snarky explanation]'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'fill_in_blank': {
        'prompt': (
            'FILLIN: [sentence with key words replaced by _____, mad-libs style]\n'
            'ANSWER: [intended words, plus a funnier alternative]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'choose_adventure': {
        'prompt': (
            'ADVENTURE: [a mini choose-your-own-adventure scenario]\n'
            'OPTION_A: [choice and funny outcome in one sentence]\n'
            'OPTION_B: [choice and funny outcome]\n'
            'OPTION_C: [choice and funny outcome]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'progress_bar': {
        'prompt': (
            'PROGRESS: [something being measured, e.g. "Progress toward enlightenment"]\n'
            'PERCENT: [a funny percentage, e.g. 47 or 103]\n'
            'NOTE: [one-line comment on the progress]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'fake_comments': {
        'prompt': (
            'COMMENTS: [title, e.g. "What people are saying"]\n'
            'USER: [username] -- [comment, 1 sentence]\n'
            'USER: [username] -- [comment]\n'
            'USER: [username] -- [comment]\n'
            '(3-4 fake comments, increasingly unhinged)'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'fake_search': {
        'prompt': (
            'SEARCHBAR: [placeholder text for a fake search input]\n'
            'SUGGESTION: [autocomplete 1]\n'
            'SUGGESTION: [autocomplete 2]\n'
            'SUGGESTION: [autocomplete 3]'
        ),
        'category': 'interactive',
        'weight': 3,
    },
    'faq': {
        'prompt': (
            'FAQ: [title]\n'
            'Q: [funny question]\nA: [unhelpful or absurd answer]\n'
            'Q: [another]\nA: [another]\n'
            '(2-3 Q&A pairs)'
        ),
        'category': 'interactive',
        'weight': 5,
    },
    'recipe': {
        'prompt': (
            'RECIPE: [title -- a fake recipe for something that is NOT food, '
            'or food described absurdly]\n'
            'INGREDIENTS:\n- [item 1]\n- [item 2]\n- [item 3]\n'
            'STEPS:\n1. [step]\n2. [step]\n3. [step]\n'
            '(3-4 each, short and funny)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'achievement': {
        'prompt': (
            'ACHIEVEMENT: [fake achievement/trophy unlocked notification]\n'
            'DESCRIPTION: [what the user "did" to earn it]'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'haiku': {
        'prompt': 'HAIKU: [a haiku (5-7-5 syllables) about the topic -- funny, weird, or deep]',
        'category': 'interactive',
        'weight': 4,
    },
    'marquee': {
        'prompt': 'MARQUEE: [scrolling text -- urgent, dramatic, or funny one-liner announcement]',
        'category': 'interactive',
        'weight': 3,
    },
    'this_or_that': {
        'prompt': (
            'THISORTHAT: [title]\n'
            'OPTION_A: [thing 1]\n'
            'OPTION_B: [thing 2]\n'
            '(presented as a "pick one" choice -- both options should be funny or hard to choose between)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
    'rating_breakdown': {
        'prompt': (
            'RATINGBREAKDOWN: [what is being rated]\n'
            'TASTE: [score]/10 -- [one-line comment]\n'
            'VIBES: [score]/10 -- [comment]\n'
            'CHAOS: [score]/10 -- [comment]\n'
            'OVERALL: [score]/10\n'
            '(3-5 funny rating categories)'
        ),
        'category': 'interactive',
        'weight': 4,
    },
}


# ======================================================================
# EXOTIC BLOCKS — low weight, no duplicates, the "wow" factor
# ======================================================================

EXOTIC_BLOCKS = {
    'alignment_chart': {
        'prompt': (
            'ALIGNMENTCHART: [title -- what are we classifying?]\n'
            'LAWFUL GOOD: [item]\nNEUTRAL GOOD: [item]\nCHAOTIC GOOD: [item]\n'
            'LAWFUL NEUTRAL: [item]\nTRUE NEUTRAL: [item]\nCHAOTIC NEUTRAL: [item]\n'
            'LAWFUL EVIL: [item]\nNEUTRAL EVIL: [item]\nCHAOTIC EVIL: [item]'
        ),
        'category': 'data',
        'weight': 2,
    },
    'bingo': {
        'prompt': (
            'BINGO: [title -- e.g. "Things That Will Definitely Happen"]\n'
            '- [square 1]\n- [square 2]\n- [square 3]\n'
            '- [square 4]\n- [square 5]\n- [square 6]\n'
            '- [square 7]\n- [square 8]\n- [square 9]\n'
            '(exactly 9 items for a 3x3 bingo card)'
        ),
        'category': 'list',
        'weight': 2,
    },
    'classified': {
        'prompt': (
            'CLASSIFIED: [fake redacted government document about the topic, '
            'use [REDACTED] blocks for comedic effect, 2-3 sentences]'
        ),
        'category': 'callout',
        'weight': 2,
    },
    'prophecy': {
        'prompt': 'PROPHECY: [a dramatic, vaguely ominous prediction about the topic, written like an ancient oracle]',
        'category': 'voice',
        'weight': 2,
    },
    'wanted_poster': {
        'prompt': (
            'WANTED: [name or thing related to the topic]\n'
            'CRIME: [fake crime, dramatic and specific]\n'
            'REWARD: [absurd reward]\n'
            'DESCRIPTION: [1-2 sentence funny description]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'award': {
        'prompt': (
            'AWARD: [fake award name, very official-sounding]\n'
            'RECIPIENT: [who or what is receiving it]\n'
            'REASON: [ridiculous reason, 1-2 sentences]\n'
            'PRESENTED_BY: [fake organization with an absurd name]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'dictionary': {
        'prompt': (
            'DICTIONARY: [fake dictionary entry for a made-up word related to the topic]\n'
            'PRONUNCIATION: [fake phonetic spelling]\n'
            'DEFINITION: [funny definition, 1-2 sentences]\n'
            'USAGE: [example sentence using the word]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'field_guide': {
        'prompt': (
            'FIELDGUIDE: [treating something in the topic like a wildlife species]\n'
            'SPECIES: [fake Latin name]\n'
            'HABITAT: [where found]\n'
            'BEHAVIOR: [1-2 sentences nature-documentary style]\n'
            'DANGER_LEVEL: [rating with funny justification]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'dating_profile': {
        'prompt': (
            'DATINGPROFILE: [treating the topic like a person on a dating app]\n'
            'AGE: [funny answer]\n'
            'LOOKING_FOR: [what the topic "wants"]\n'
            'BIO: [2-3 sentence bio in the voice of the topic]\n'
            'DEALBREAKER: [one funny dealbreaker]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'horoscope': {
        'prompt': (
            'HOROSCOPE: [fake horoscope or fortune cookie prediction related to the topic, '
            '2-3 sentences, vague but dramatic]\n'
            'LUCKY_NUMBER: [a number with a funny reason]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'equation': {
        'prompt': (
            'EQUATION: [fake mathematical formula related to the topic, '
            'real-looking notation but nonsensical variables, '
            'e.g. "Fun = (Tacos x Friday) / Responsibility squared"]\n'
            'PROOF: [one-sentence fake proof or citation]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'transcript': {
        'prompt': (
            'TRANSCRIPT: [title -- fake transcript of what]\n'
            'SPEAKER1: [name] -- [line]\nSPEAKER2: [name] -- [line]\n'
            'SPEAKER1: [name] -- [line]\nSPEAKER2: [name] -- [line]\n'
            '(4-6 lines, escalating absurdity)'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'coupon': {
        'prompt': (
            'COUPON: [fake coupon related to the topic]\n'
            'DISCOUNT: [what you get]\n'
            'CODE: [funny promo code]\n'
            'EXPIRES: [absurd condition, e.g. "When the moon turns blue"]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'postcard': {
        'prompt': (
            'POSTCARD: [fake postcard message, 2-3 sentences "wish you were here" energy]\n'
            'FROM: [who sent it]\nTO: [who it\'s addressed to]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'footnote': {
        'prompt': (
            'FOOTNOTE: [fake academic footnote that starts reasonable and derails '
            'into something absurd or deeply personal, 2-3 sentences]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'obituary': {
        'prompt': (
            'OBITUARY: [a fake obituary for a concept, trend, or thing related to the topic]\n'
            'BORN: [when it started]\nDIED: [when/how it ended]\n'
            'SURVIVED_BY: [what it left behind]\n'
            'MEMORIAL: [how to honor its memory, funny]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'court_ruling': {
        'prompt': (
            'COURTRULING: [fake court case name, e.g. "The People vs. Pineapple Pizza"]\n'
            'CHARGE: [what the accused is charged with]\n'
            'VERDICT: [guilty/not guilty and the reasoning, 1-2 sentences]\n'
            'SENTENCE: [the punishment, absurd]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'autopsy_report': {
        'prompt': (
            'AUTOPSY: [fake autopsy/incident report for a failed project, trend, or idea related to the topic]\n'
            'CAUSE_OF_DEATH: [what went wrong]\n'
            'TIME_OF_DEATH: [when it died]\n'
            'CONTRIBUTING_FACTORS: [2-3 bullet points of funny reasons]\n'
            'EXAMINER_NOTES: [one-line snarky final observation]'
        ),
        'category': 'data',
        'weight': 1,
    },
    'text_message': {
        'prompt': (
            'TEXTCHAIN: [title -- who is texting who]\n'
            'MSG: [sender] > [short text message]\n'
            'MSG: [other] > [reply]\n'
            'MSG: [sender] > [reply]\n'
            'MSG: [other] > [reply]\n'
            '(4-6 messages, like a screenshot of a funny text exchange)'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'yelp_review': {
        'prompt': (
            'YELPREVIEW: [treating the topic like a restaurant or business]\n'
            'STARS: [1-5]\n'
            'REVIEW: [2-3 sentence fake Yelp review, passive-aggressive or weirdly specific]\n'
            'REVIEWER: [fake name]\n'
            'HELPFUL: [X out of Y people found this helpful -- funny numbers]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'weather_report': {
        'prompt': (
            'WEATHER: [fake weather forecast for the topic as if it were a location]\n'
            'TODAY: [condition and temperature, funny]\n'
            'TOMORROW: [forecast]\n'
            'WEEKEND: [forecast]\n'
            'ADVISORY: [fake weather advisory, dramatic]'
        ),
        'category': 'data',
        'weight': 1,
    },
    'resume': {
        'prompt': (
            'RESUME: [the topic presented as a job applicant\'s resume]\n'
            'OBJECTIVE: [what the topic "wants"]\n'
            'EXPERIENCE: [2-3 bullet points of fake work history]\n'
            'SKILLS: [3-4 fake skills]\n'
            'REFERENCES: [funny "available upon request" variant]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'product_recall': {
        'prompt': (
            'RECALL: [fake product recall notice related to the topic]\n'
            'PRODUCT: [what is being recalled]\n'
            'REASON: [absurd safety concern]\n'
            'ACTION: [what consumers should do, funny]\n'
            'AFFECTED_UNITS: [ridiculous number]'
        ),
        'category': 'callout',
        'weight': 1,
    },
    'police_report': {
        'prompt': (
            'POLICEREPORT: [fake incident report related to the topic]\n'
            'INCIDENT: [what happened]\n'
            'SUSPECT: [description, funny]\n'
            'WITNESSES: [what witnesses said, contradictory or absurd]\n'
            'STATUS: [case status, e.g. "Under investigation by the Fun Police"]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'mad_lib': {
        'prompt': (
            'MADLIB: [a 3-4 sentence paragraph about the topic with 4-6 words replaced by '
            'their part of speech in brackets, e.g. "The [ADJECTIVE] [NOUN] decided to [VERB]..."]\n'
            'ANSWERS: [the intended funny answers for each blank]'
        ),
        'category': 'interactive',
        'weight': 2,
    },
    'stock_ticker': {
        'prompt': (
            'STOCKTICKER: [treating aspects of the topic like stocks]\n'
            'SYMBOL: [3-4 letter ticker] -- [name] -- [price] -- [change with arrow up/down] -- [funny reason]\n'
            'SYMBOL: [ticker] -- [name] -- [price] -- [change] -- [reason]\n'
            'SYMBOL: [ticker] -- [name] -- [price] -- [change] -- [reason]\n'
            '(3-4 fake stock entries)'
        ),
        'category': 'data',
        'weight': 1,
    },
    'conspiracy': {
        'prompt': (
            'CONSPIRACY: [a fake conspiracy theory about the topic, '
            'written with escalating conviction and connecting random dots, '
            '3-4 sentences that start reasonable and end unhinged]'
        ),
        'category': 'voice',
        'weight': 2,
    },
    'survival_guide': {
        'prompt': (
            'SURVIVALGUIDE: [title -- "How to Survive [topic-related scenario]"]\n'
            'STEP1: [first thing to do]\n'
            'STEP2: [second thing]\n'
            'STEP3: [third thing, increasingly absurd]\n'
            'PROTIP: [one final piece of dubious wisdom]'
        ),
        'category': 'list',
        'weight': 2,
    },
    'infomercial': {
        'prompt': (
            'INFOMERCIAL: [fake infomercial script for a product related to the topic]\n'
            'PROBLEM: [dramatic description of a non-problem]\n'
            'SOLUTION: [the amazing product]\n'
            'BUTWAITSMORE: [bonus offer, increasingly ridiculous]\n'
            'CALLNOW: [fake phone number and urgency, e.g. "1-800-NOT-REAL -- operators are standing by!"]'
        ),
        'category': 'callout',
        'weight': 1,
    },
    'yearbook_superlative': {
        'prompt': (
            'YEARBOOK: [treating things in the topic like high school seniors]\n'
            'MOST_LIKELY_TO_SUCCEED: [item]\n'
            'CLASS_CLOWN: [item]\n'
            'BEST_HAIR: [item]\n'
            'MOST_CHANGED: [item]\n'
            'BEST_COUPLE: [item A] & [item B]\n'
            '(5-7 superlatives, each one line)'
        ),
        'category': 'list',
        'weight': 1,
    },
    'loading_bar_story': {
        'prompt': (
            'LOADINGSTORY: [a progress bar that tells a story as it loads]\n'
            '10%%: [status message]\n'
            '35%%: [status, things getting weird]\n'
            '67%%: [status, something has gone wrong]\n'
            '89%%: [status, existential crisis]\n'
            '100%%: [final status, anticlimax or punchline]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'complaint_form': {
        'prompt': (
            'COMPLAINTFORM: [title -- fake official complaint form]\n'
            'FIELD: Name: [pre-filled funny name]\n'
            'FIELD: Nature of complaint: [pre-filled absurd complaint]\n'
            'FIELD: Desired resolution: [unreasonable demand]\n'
            'FIELD: How angry are you (1-10): [number higher than 10]\n'
            'OFFICE_USE_ONLY: [snarky internal note]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'wikipedia_vandalism': {
        'prompt': (
            'WIKIVANDAL: [a fake Wikipedia-style paragraph about the topic that has been '
            '"vandalized" with obviously wrong edits in brackets, '
            'e.g. "The Eiffel Tower, located in [Gary, Indiana], was built in [1997] by [my uncle Steve]..."]'
        ),
        'category': 'voice',
        'weight': 1,
    },
    'email_chain': {
        'prompt': (
            'EMAILCHAIN: [subject line]\n'
            'FROM: [sender] -- [1-2 sentence email about the topic]\n'
            'RE: [responder] -- [reply]\n'
            'RE:RE: [original sender] -- [reply that escalates]\n'
            'RE:RE:RE: [responder] -- [final reply, passive-aggressive or unhinged]\n'
            '(like a screenshot of a corporate email thread gone wrong)'
        ),
        'category': 'interactive',
        'weight': 1,
    },
    'instruction_manual': {
        'prompt': (
            'MANUAL: [title -- fake instruction manual for something related to the topic]\n'
            'STEP1: [instruction with unnecessary warning]\n'
            'STEP2: [instruction that assumes too much]\n'
            'STEP3: [instruction that contradicts step 1]\n'
            'TROUBLESHOOTING: [one FAQ-style troubleshoot that is deeply unhelpful]\n'
            'WARRANTY: [absurd warranty terms]'
        ),
        'category': 'interactive',
        'weight': 1,
    },
}

# Category labels for balanced selection
BLOCK_CATEGORIES = ['structure', 'voice', 'list', 'data', 'callout', 'interactive']


# ---------------------------------------------------------------------------
# DYNAMIC PALETTE SELECTION
# ---------------------------------------------------------------------------

def _weighted_sample(pool: dict, k: int, exclude: set = None) -> list:
    """
    Select k items from a block pool using weighted random sampling
    WITHOUT replacement. Returns list of block keys.
    """
    if exclude is None:
        exclude = set()

    candidates = [(key, block['weight']) for key, block in pool.items() if key not in exclude]
    if not candidates:
        return []

    k = min(k, len(candidates))
    keys, weights = zip(*candidates)
    selected = []

    # Weighted sampling without replacement
    keys = list(keys)
    weights = list(weights)
    for _ in range(k):
        if not keys:
            break
        total = sum(weights)
        probs = [w / total for w in weights]
        idx = random.choices(range(len(keys)), weights=probs, k=1)[0]
        selected.append(keys[idx])
        keys.pop(idx)
        weights.pop(idx)

    return selected


def _get_all_blocks_by_category(tier_pool: dict) -> dict:
    """Group block keys by category from a given tier pool."""
    by_cat = {}
    for key, block in tier_pool.items():
        cat = block['category']
        by_cat.setdefault(cat, []).append(key)
    return by_cat


def select_block_palette() -> list:
    """
    Build a unique block palette for this generation.

    Structure:
      1. Pick 3-5 STAPLE blocks (can include duplicates of the same type)
      2. Pick 4-7 COMMON blocks (no dupes, weighted, category-diverse)
      3. Pick 1-3 EXOTIC blocks (no dupes, weighted, rare surprises)

    Total target: 10-15 blocks per palette.

    Category diversity: at least one common/exotic pick comes from each
    category that has available blocks.
    """
    palette = []

    # --- STAPLES (allow duplicates) ---
    num_staples = random.randint(3, 5)
    staple_keys = list(STAPLE_BLOCKS.keys())
    staple_weights = [STAPLE_BLOCKS[k]['weight'] for k in staple_keys]

    for _ in range(num_staples):
        pick = random.choices(staple_keys, weights=staple_weights, k=1)[0]
        palette.append(('staple', pick))

    # --- COMMONS (no dupes, category-diverse) ---
    num_commons = random.randint(4, 7)
    used_common_keys = set()

    # Phase 1: one from each category that has common blocks
    common_by_cat = _get_all_blocks_by_category(COMMON_BLOCKS)
    for cat in BLOCK_CATEGORIES:
        cat_pool = common_by_cat.get(cat, [])
        if cat_pool:
            candidates = [(k, COMMON_BLOCKS[k]['weight']) for k in cat_pool]
            keys_c, weights_c = zip(*candidates)
            pick = random.choices(keys_c, weights=weights_c, k=1)[0]
            used_common_keys.add(pick)
            palette.append(('common', pick))

    # Phase 2: fill remaining common slots
    remaining_common = max(0, num_commons - len(used_common_keys))
    if remaining_common > 0:
        extra = _weighted_sample(COMMON_BLOCKS, remaining_common, exclude=used_common_keys)
        for k in extra:
            used_common_keys.add(k)
            palette.append(('common', k))

    # --- EXOTICS (no dupes, weighted) ---
    num_exotics = random.choices([1, 2, 3], weights=[40, 40, 20], k=1)[0]
    exotic_picks = _weighted_sample(EXOTIC_BLOCKS, num_exotics)
    for k in exotic_picks:
        palette.append(('exotic', k))

    # Shuffle the full palette so block order varies
    random.shuffle(palette)

    logger.info(
        f"Palette: {len(palette)} blocks "
        f"({sum(1 for t,_ in palette if t=='staple')} staple, "
        f"{sum(1 for t,_ in palette if t=='common')} common, "
        f"{sum(1 for t,_ in palette if t=='exotic')} exotic)"
    )

    return palette


def build_block_prompt_section(palette: list) -> str:
    """
    Build the content block instructions section of the system prompt
    from the selected palette.

    Handles duplicate staple keys by including the prompt text once
    with a note that multiple instances can be used.
    """
    all_pools = {**STAPLE_BLOCKS, **COMMON_BLOCKS, **EXOTIC_BLOCKS}

    # Count occurrences of each key
    from collections import Counter
    key_counts = Counter(key for _, key in palette)

    lines = ['=== CONTENT BLOCK TYPES (use these for this page) ===', '']

    seen = set()
    for _, key in palette:
        if key in seen:
            continue
        seen.add(key)

        block = all_pools[key]
        lines.append(block['prompt'])
        if key_counts[key] > 1:
            lines.append(f'(you may use this block type up to {key_counts[key]} times on this page)')
        lines.append('')

    lines.append('=== END BLOCK TYPES ===')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# STAGE 1: CONTENT GENERATION
# ---------------------------------------------------------------------------

CONTENT_SYSTEM_PROMPT_TEMPLATE = """You are a chaotic, creative web content generator. You make pages
that are FUN to skim -- not essays to study. Think "weird internet energy" meets "someone
had too much fun building this." Every page should make someone laugh, raise an eyebrow,
or screenshot it to send to a friend.

=== PAGE NARRATIVE ARC ===

Every page tells a STORY, even if it's absurd. Think of it like a magazine article or a
comedy bit -- not a random bag of blocks dumped on a page. Structure your page like this:

OPENING (first 2-3 blocks): Hook the reader. Set the tone. Introduce the topic with
  energy. The title and subtitle do heavy lifting here, then a strong opening paragraph
  or section that establishes the "angle" -- the specific spin or premise you're taking
  on this topic.

MIDDLE (5-8 blocks): Build on the premise. Each block should REACT TO or BUILD ON what
  came before. A ranking should rank things mentioned earlier. A testimonial should quote
  someone responding to a claim you just made. A warning should warn about something the
  content just described. Stats should "prove" something you asserted. Use plain blocks
  (PARAGRAPH, LIST, etc.) as connective tissue BETWEEN the fun blocks -- a sentence that
  transitions, reacts, or sets up what's coming next.

CLOSER (2-3 blocks): Land the plane. Callback to something from the opening. End with
  something punchy -- a mic drop, a final verdict, a dramatic sign-off, a callback joke.
  The reader should feel like the page ENDED, not just stopped.

=== CRITICAL: MAKING BLOCKS FLOW TOGETHER ===

The #1 mistake is blocks that feel like isolated islands. AVOID THIS by:

- REFERENCING EARLIER CONTENT: If a section mentions "the legendary 1987 incident", a
  later testimonial should quote someone who was "there in '87". A warning should say
  "given what we just learned above..."

- RUNNING BITS: Introduce a character, concept, or joke early and bring it back. A fake
  expert quoted in paragraph 2 could show up again in a testimonial later. A made-up
  statistic could be "disproven" in a later debate block.

- TRANSITIONS: Between blocks, the last line of one block should set up the next. End a
  section with "But not everyone agrees..." before a DEBATE block. End a ranking with
  "Speaking of #1..." before diving deeper.

- SHARED VOCABULARY: Use the same funny names, made-up terms, and specific references
  across multiple blocks. If you invent "Dr. Crunchwhistle" in a quote, have them appear
  in a testimonial or complaint later.

- ESCALATION: The page should get progressively more unhinged. Start somewhat grounded
  and let the absurdity build. The last few blocks should be the wildest.

=== OUTPUT FORMAT ===

Use these markers. Mix and match freely. NOT EVERY MARKER NEEDS TO APPEAR.
Pick 10-16 blocks total.

TITLE: [funny, dramatic, or absurd page title]
SUBTITLE: [punchy one-liner or tagline]

IMAGE: [3-5 word description for image search]
CAPTION: [funny or descriptive caption]
(include 1-3 images placed naturally throughout the page)

{DYNAMIC_BLOCKS}

RULES:
- Use 10-16 content blocks per page -- variety over volume
- Keep paragraphs SHORT: 2-3 sentences max, not 5-6
- Be funny, weird, confident, and entertaining
- Invent fake statistics, quotes, testimonials, and facts with total conviction
- Every page should feel like ONE cohesive piece, not a collection of unrelated blocks
- DO NOT just write section after section of paragraphs -- MIX UP the block types
- Use plain blocks (PARAGRAPH, LIST, TABLE, etc.) as TRANSITIONS between fun blocks
- At least 5 different block types must appear on every page
- EVERY block should reference, react to, or build on something from another block
- DO NOT write HTML tags -- just plaintext with the markers above
- DO NOT write CSS or styling instructions
- Match explicit content if input is explicit
- Never create content harmful to minors
- Expand upon any outlandish or nonsensical themes
- The tone should lean comedic/absurd unless the input is clearly serious
"""


def generate_content(prompt: str, active_effects: list, temperature: float = 0.85) -> str:
    """Stage 1: Generate entertaining, varied content from the user's prompt."""

    # Select this generation's unique block palette
    palette = select_block_palette()
    dynamic_section = build_block_prompt_section(palette)
    system = CONTENT_SYSTEM_PROMPT_TEMPLATE.replace('{DYNAMIC_BLOCKS}', dynamic_section)

    # Log what exotics were picked (the interesting part)
    exotic_picks = [k for t, k in palette if t == 'exotic']
    logger.info(f"Exotic blocks this generation: {exotic_picks}")

    # Check for style effects
    style_effect = next(
        (e for e in active_effects if e.effect_type == 'generation_style'), None
    )
    if style_effect:
        style_instructions = _get_style_instructions(style_effect.effect_value)
        if style_instructions:
            system = style_instructions + "\n\n" + system

    # Flavor injections -- push the model toward different vibes each time
    flavor_angles = [
        "Include a completely unhinged fake testimonial.",
        "Add a dramatic WARNING box about something absurd.",
        "Include a fake poll with ridiculous answer options.",
        "Add made-up statistics that sound just real enough to be funny.",
        "Include a fake breaking news alert.",
        "Add a ranking/top list with spicy hot takes.",
        "Include a ridiculous fake advertisement.",
        "Add a timeline of fictional events.",
        "Include a DEBATE section with two opposing absurd takes.",
        "Add comparison content that's unexpected.",
        "Include a conspiracy-theory-style fun fact.",
        "Add fake expert quotes from people with ridiculous job titles.",
        "Include a fake error message or loading screen.",
        "Add a choose-your-own-adventure moment.",
        "Include a fake dictionary entry for a made-up word.",
        "Add a nature-documentary-style field guide entry.",
        "Include a fake coupon or promotional offer.",
        "Include a mic-drop one-liner.",
        "Add a before-and-after comparison.",
        "Include a fake flowchart decision tree.",
        "Add a rant that escalates hilariously.",
        "Include a scoreboard or leaderboard.",
    ]
    selected_flavors = random.sample(flavor_angles, k=random.randint(2, 4))

    enhanced_prompt = f"""Create a fun, skimmable page about: {prompt}

Your angle/premise for this page (pick ONE and commit to it throughout):
Think of a specific funny take, framing, or "bit" for this topic. Not just "here's stuff about [topic]"
but "what if [topic] was [unexpected angle]" -- then make every block serve that premise.

Make sure to include:
{chr(10).join('- ' + f for f in selected_flavors)}

CRITICAL: The blocks should feel like ONE flowing piece. Reference earlier content in later blocks.
Reuse character names, callback to jokes, escalate the absurdity. Transitions between blocks matter."""

    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": enhanced_prompt}
        ],
        max_tokens=4000,
        temperature=temperature,
        top_p=0.92
    )

    content = response.choices[0].message.content.strip()
    logger.info(f"Stage 1 produced {len(content)} chars of content")
    return content


# ---------------------------------------------------------------------------
# STAGE 2: HTML STRUCTURE
# ---------------------------------------------------------------------------

STRUCTURE_SYSTEM_PROMPT = """You convert structured plaintext content into semantic, varied HTML5.
The input uses content markers -- map each to a DISTINCT HTML pattern so the page feels visually
diverse, not like a wall of identical sections.

INPUT MARKER -> HTML MAPPING (use these, plus infer mappings for any unlisted markers):

=== CORE ===
TITLE -> <h1> in <header>
SUBTITLE -> <p class="subtitle"> in <header>
IMAGE/CAPTION -> <figure> with <img> (src="placeholder.jpg", alt from description) and <figcaption>

=== STAPLE / PLAIN ===
PARAGRAPH -> <p> or <div class="content-paragraph"> (standalone paragraph)
SECTION -> <section> with <h2> heading and <p> body
LIST -> <div class="content-list"> with <h3> title and <ul>
NUMBEREDLIST -> <div class="numbered-list"> with <h3> title and <ol>
TABLE -> <div class="content-table"> with <h3> title and <table>
HEADING/TEXT -> <div class="heading-text"> with <h2> and <p>
CALLOUT/CONTENT -> <div class="callout-box"> with emoji/label and text
DIVIDER -> <div class="divider-text"> centered decorative text
BOLD -> <div class="bold-statement"> large centered text
CAPTIONBLOCK -> <div class="caption-block"> small formatted text
SUMMARY/CONTENT -> <div class="summary-box"> with title and text
KEYVALUE -> <div class="key-value"> with <dl> definition list
BLOCKQUOTE/SOURCE -> <blockquote> with <cite>

=== COMMON ===
FUNFACT -> <aside class="funfact"> with lightbulb emoji and bold text
QUOTE/ATTRIBUTION -> <blockquote class="fancy-quote"> with <cite>
TESTIMONIAL/AUTHOR -> <div class="testimonial"> with <blockquote> and <footer>
DEBATE/COUNTERPOINT -> <div class="debate"> two opposing <div> blocks side by side
HOTTAKE -> <div class="hot-take"> bold, flame emoji
UNPOPULAROPINION/DEFENSE -> <div class="unpopular-opinion"> split layout
OVERHEARD -> <div class="overheard"> chat bubble styling
REVIEW/STARS/REVIEWER -> <div class="review-card"> star rating and quote
COMPLAINT/SIGNED -> <div class="complaint-card"> angry letter styling
CONFESSION -> <div class="confession"> anonymous post styling
RANT -> <div class="rant"> escalating text styling
MICDROP -> <div class="mic-drop"> large bold centered text, mic emoji
RANKING -> <div class="ranking"> with <ol>
TIPS -> <div class="tips"> with <ul>
STATS -> <div class="stats"> with stat items
TIERLIST -> <div class="tier-list"> colored tier rows
PROSCONS/VERDICT -> <div class="pros-cons"> two-column layout
CHECKLIST -> <div class="checklist"> checkbox inputs
STARTERPACK -> <div class="starter-pack"> grid of items
DODONT -> <div class="do-dont"> two-column do/don't layout
SUPERLATIVES -> <div class="superlatives"> award-style list
COMPARISON -> <div class="comparison"> side-by-side
TIMELINE -> <div class="timeline"> vertical timeline
POLL/OPTIONS -> <div class="poll"> radio buttons
SCALE/VERDICT -> <div class="scale-meter"> range element
MATCHUP/ROUNDS/CHAMPION -> <div class="matchup"> fight card styling
SPECTRUM -> <div class="spectrum"> horizontal bar with markers
FLOWCHART -> <div class="flowchart"> decision tree with arrows/connections
BEFOREAFTER/VERDICT -> <div class="before-after"> split comparison
SCOREBOARD -> <div class="scoreboard"> leaderboard table
WARNING -> <div class="warning-box"> bold border, warning emoji
BREAKING -> <div class="breaking-news"> red banner, alert emoji
AD -> <div class="fake-ad"> promotional callout
SIDEBAR -> <aside class="sidebar"> offset content
DISCLAIMER -> <div class="disclaimer"> small legal-style text
ERROR -> <div class="error-message"> crash screen styling
NOTIFICATION -> <div class="notification"> phone notification card
TICKER -> <div class="news-ticker"> scrolling <marquee> or container
LOADING/PERCENT -> <div class="fake-loading"> <progress> bar
PSA -> <div class="psa"> public service announcement box
UPDATE -> <div class="update-banner"> blog-style edit notice
SPOILER/CONTENT -> <details class="spoiler"> with <summary>
SECRET/REVEAL -> <details class="secret"> with <summary>
QUIZ/ANSWER -> <div class="quiz"> form with radio buttons and hidden answer
FILLIN/ANSWER -> <div class="fill-in-blank"> inputs in text
ADVENTURE/OPTIONS -> <div class="choose-adventure"> option cards
PROGRESS/PERCENT/NOTE -> <div class="progress-widget"> <progress> and label
COMMENTS -> <div class="fake-comments"> comment thread blocks
SEARCHBAR/SUGGESTIONS -> <div class="fake-search"> input with dropdown
ACHIEVEMENT -> <div class="achievement-unlocked"> game popup styling
RECIPE/INGREDIENTS/STEPS -> <div class="fake-recipe"> recipe card
HAIKU -> <div class="haiku"> centered, italicized
MARQUEE -> <marquee> with text
FAQ -> <div class="faq"> with <details>/<summary> Q&A
THISORTHAT -> <div class="this-or-that"> two option cards side by side
RATINGBREAKDOWN -> <div class="rating-breakdown"> category scores with bars

=== EXOTIC ===
ALIGNMENTCHART -> <div class="alignment-chart"> 3x3 grid table
BINGO -> <div class="bingo-card"> 3x3 grid table
CLASSIFIED/REDACTED -> <div class="classified-doc"> monospace, redaction bars
PROPHECY -> <div class="prophecy"> mystical/oracle styling
WANTED/CRIME/REWARD -> <div class="wanted-poster"> western poster styling
AWARD/RECIPIENT/REASON -> <div class="award-card"> certificate styling
DICTIONARY/PRONUNCIATION/DEFINITION/USAGE -> <div class="dictionary-entry"> dictionary page
FIELDGUIDE/SPECIES -> <div class="field-guide"> nature encyclopedia card
DATINGPROFILE/BIO -> <div class="dating-profile"> app profile card
HOROSCOPE/LUCKY_NUMBER -> <div class="horoscope"> mystical zodiac card
EQUATION/PROOF -> <div class="equation"> monospace math styling
TRANSCRIPT -> <div class="transcript"> screenplay format
COUPON/DISCOUNT/CODE/EXPIRES -> <div class="coupon"> tear-off coupon styling
POSTCARD/FROM/TO -> <div class="postcard"> postcard with handwriting feel
FOOTNOTE -> <div class="footnote"> small numbered reference
OBITUARY -> <div class="obituary"> memorial/newspaper obituary styling
COURTRULING -> <div class="court-ruling"> legal document styling
AUTOPSY -> <div class="autopsy-report"> clinical report styling
TEXTCHAIN -> <div class="text-chain"> iMessage/SMS bubble styling
YELPREVIEW -> <div class="yelp-review"> Yelp-style review card
WEATHER -> <div class="weather-report"> weather forecast card
RESUME -> <div class="resume"> resume/CV document styling
RECALL -> <div class="product-recall"> official recall notice styling
POLICEREPORT -> <div class="police-report"> incident report form styling
MADLIB -> <div class="mad-lib"> paragraph with input blanks
STOCKTICKER -> <div class="stock-ticker"> financial ticker display
CONSPIRACY -> <div class="conspiracy"> corkboard/red-string styling
SURVIVALGUIDE -> <div class="survival-guide"> field manual styling
INFOMERCIAL -> <div class="infomercial"> TV infomercial callout
YEARBOOK -> <div class="yearbook"> yearbook page styling
LOADINGSTORY -> <div class="loading-story"> animated progress narrative
COMPLAINTFORM -> <div class="complaint-form"> official form with fields
WIKIVANDAL -> <div class="wiki-vandal"> Wikipedia article with edit marks
EMAILCHAIN -> <div class="email-chain"> threaded email styling
MANUAL -> <div class="instruction-manual"> technical manual styling

DOCUMENT STRUCTURE:
1. Complete HTML5 document: <!DOCTYPE html>, <html lang="en">, <head>, <body>
2. <head> must include meta charset, viewport, and <title>
3. Wrap everything in <main> with <header> at top and <footer> at bottom
4. Each content block should be its own distinct HTML element

PAGE FLOW -- MAKING IT FEEL CONNECTED:
1. Add short <p class="transition"> elements between blocks when the content has a
   natural transition phrase (e.g. "But that's not all...", "Speaking of which...",
   "Now here's where it gets interesting..."). If the plaintext content has transition
   sentences, put them in these elements rather than inside the blocks themselves.
2. Group related blocks inside <div class="content-cluster"> containers when 2-3 blocks
   clearly relate to each other (e.g. a section followed by a testimonial reacting to it).
   This creates visual grouping without breaking individual block styling.
3. Use <hr class="section-break"> between major topic shifts to create intentional
   pacing, but NOT between every single block.
4. The <header> should feel like a magazine cover -- title, subtitle, and optionally
   the first image or a hook paragraph, all grouped together.
5. The last 1-2 blocks before <footer> should feel like a deliberate ending -- wrap
   them in <div class="page-closer"> to signal visual finality.

CRITICAL RULES:
- Every block type should produce VISUALLY DIFFERENT HTML structure
- DO NOT just wrap everything in <section><p> -- use the varied elements listed
- If you encounter a marker not listed above, infer appropriate HTML with a descriptive class name
- Preserve ALL content text exactly as provided
- DO NOT add CSS or styling -- just semantic HTML with descriptive class names
- Output raw HTML only -- no explanations
"""


def build_html_structure(content: str) -> str:
    """Stage 2: Convert structured text content into semantic HTML5."""

    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=STRUCTURE_MODEL,
        messages=[
            {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ],
        max_tokens=7000,
        temperature=0.3,
        top_p=0.95
    )

    html = response.choices[0].message.content.strip()
    logger.info(f"Stage 2 produced {len(html)} chars of HTML")
    return html


# ---------------------------------------------------------------------------
# STAGE 3: STYLING
# ---------------------------------------------------------------------------

STYLING_SYSTEM_PROMPT = """You are a Tailwind CSS expert who makes FUN, visually diverse web pages.
Style the provided HTML using ONLY Tailwind utility classes.

BLOCK-SPECIFIC STYLING (make each block type look DIFFERENT):

=== STAPLE / PLAIN BLOCKS ===
- p, .content-paragraph -> readable, comfortable spacing, slightly larger text
- .content-list -> card background, styled bullets, padded
- .numbered-list -> large bold numbers, card items
- .content-table -> striped rows, rounded, shadow, colored header
- .heading-text -> large heading with accent underline, body text below
- .callout-box -> colored left border, padded, accent background
- .divider-text -> centered, decorative, muted color, spacing above/below
- .bold-statement -> text-2xl or text-3xl, centered, font-bold, accent color
- .caption-block -> small text, italic, bordered, museum-placard feel
- .summary-box -> card with header bar, padded content
- .key-value -> alternating row backgrounds, label bold, value normal
- blockquote -> large italic text, decorative left border

=== COMMON BLOCKS ===
- .funfact -> bright accent background, rounded, padded, tilted feel
- .warning-box -> red/orange/yellow background, bold border, dramatic
- .ranking -> large bold numbers, card-style items
- .testimonial -> italic text, decorative quote marks, subtle background
- .poll -> card with radio buttons, interactive feel, bordered
- .debate -> two-column layout (flex/grid), contrasting colors
- .tips -> clean list with bullets, card background
- .comparison -> side-by-side or highlighted box
- .timeline -> vertical line with dots, staggered entries
- .breaking-news -> bold red banner, all-caps, dramatic urgency
- .fake-ad -> cheesy bright background, rounded, "click here" energy
- .stats -> large bold numbers, grid layout, eye-catching
- .sidebar -> offset background, smaller text, border-left accent
- .hot-take -> fire emoji, bold, attention-grabbing background
- .unpopular-opinion -> split layout for opinion vs defense
- .overheard -> chat bubble styling, alternating alignment
- .review-card -> star display, card layout, footer
- .complaint-card -> angry red accents, letter feel
- .confession -> dark background, anonymous feel
- .rant -> escalating text size or intensity
- .mic-drop -> huge centered text, dramatic spacing
- .tier-list -> colored rows (S=gold, A=green, B=blue, C=orange, F=red)
- .pros-cons -> two-column green/red with verdict banner
- .checklist -> checkbox styling, card background
- .starter-pack -> grid of items, meme-style
- .do-dont -> two-column green DO / red DONT
- .superlatives -> award-ribbon styling, gold accents
- .scale-meter -> visual meter, colored gradient
- .matchup -> fight-card styling, versus divider
- .spectrum -> horizontal bar with markers, gradient
- .flowchart -> boxes connected by arrows, decision-tree look
- .before-after -> split screen, left/right comparison
- .scoreboard -> leaderboard table, medal colors for top 3
- .disclaimer -> tiny text, bordered box, legal feel
- .fake-loading -> progress bar, monospace, tech feel
- .error-message -> red/dark background, monospace, crash screen
- .notification -> phone notification card, rounded, shadow
- .news-ticker -> horizontal scroll, red/dark banner
- .psa -> official-looking, bordered, serious-tone card
- .update-banner -> yellow/orange highlight, editorial feel
- .spoiler, .secret -> clickable details/summary, styled toggle
- .quiz -> card with options, interactive feel
- .fill-in-blank -> inline input fields in text
- .choose-adventure -> option cards in grid, hover effects
- .progress-widget -> styled progress bar with label
- .fake-comments -> avatars (initials), comment bubbles, thread
- .fake-search -> search input with dropdown, Google-like
- .achievement-unlocked -> game popup, gold/trophy, celebration
- .fake-recipe -> recipe card, ingredients sidebar, numbered steps
- .haiku -> centered, whitespace, elegant minimal
- .faq -> clean accordion style
- .this-or-that -> two large option cards, "VS" in middle
- .rating-breakdown -> horizontal score bars, category labels

=== EXOTIC BLOCKS ===
- .alignment-chart -> 3x3 grid with colored cells, D&D aesthetic
- .bingo-card -> grid layout, bordered cells, fun backgrounds
- .classified-doc -> black/dark background, green/white monospace, redaction bars
- .prophecy -> dark/mystical background, ornate text, centered
- .wanted-poster -> old western style, sepia tones, bold WANTED
- .award-card -> certificate style, gold accents, formal
- .dictionary-entry -> serif font feel, structured definition
- .field-guide -> nature encyclopedia, bordered specimen card
- .dating-profile -> app card, profile layout, swipe energy
- .horoscope -> mystical/zodiac, purple/dark blues, stars
- .equation -> monospace, centered, chalkboard feel
- .transcript -> screenplay format, bold speakers, indented
- .coupon -> dashed border, tear-off style, bold discount
- .postcard -> rounded, slight tilt, handwriting font feel
- .footnote -> small text, numbered, offset
- .obituary -> newspaper obituary, bordered, solemn-but-funny
- .court-ruling -> legal document, serif, official seal feel
- .autopsy-report -> clinical, monospace, form-field styling
- .text-chain -> iMessage/SMS bubbles, blue/gray, timestamps
- .yelp-review -> Yelp red, star display, helpful count
- .weather-report -> weather card, icons, forecast grid
- .resume -> CV styling, sections, clean professional
- .product-recall -> official notice, red header, urgent
- .police-report -> form fields, monospace, incident styling
- .mad-lib -> paragraph with highlighted input blanks
- .stock-ticker -> financial display, green/red arrows, monospace numbers
- .conspiracy -> corkboard brown, red string connections, pinned notes feel
- .survival-guide -> field manual, olive/military colors, numbered steps
- .infomercial -> TV-style, bright yellow/red, "CALL NOW" energy
- .yearbook -> yearbook page, school colors, portrait-style layout
- .loading-story -> progress bar with narrative stages
- .complaint-form -> official form fields, pre-filled, bureaucratic
- .wiki-vandal -> Wikipedia styling with obvious red edit marks
- .email-chain -> threaded emails, indented replies, gray backgrounds
- .instruction-manual -> technical manual, diagrams feel, numbered sections

GENERAL RULES:
1. Add Tailwind classes to EVERY element
2. Use vibrant, varied colors -- each block should have its OWN color scheme
3. The page should look like a fun magazine/blog, NOT a corporate report
4. Make it responsive (sm:, md:, lg: breakpoints)
5. Use rounded corners, shadows, and spacing generously
6. Add the Tailwind CDN: <script src="https://cdn.tailwindcss.com"></script>
7. Give the body a colorful background -- NOT white, NOT gray
8. Vary section widths -- not everything should be full-width

PAGE FLOW STYLING (these make the page feel CONNECTED, not just stacked):
- .transition -> text-center, italic, text-gray-500/400, my-2, text-sm or text-base.
  These are the connective phrases between blocks. They should feel like gentle
  nudges, NOT like their own big content blocks. Subtle and small.
- .content-cluster -> group related blocks with a shared subtle background or
  left border accent. Use p-4 or p-6 with rounded-lg and a very light background
  to visually group 2-3 blocks without making them feel boxed in.
- hr.section-break -> styled as a decorative divider. NOT a plain gray line.
  Use a fun pattern: a row of emojis, a gradient line, a dashed colorful border,
  or a styled hr with custom color. Should feel intentional and designed.
- .page-closer -> the final 1-2 blocks. Give them extra emphasis: larger text,
  a distinctive background color, or a "finale" feel. The reader should sense
  "this is the ending."
- header -> should feel like a cohesive opening unit. Title, subtitle, and any
  opening content should share a background or visual treatment that groups them
  as the "intro." Think magazine cover or blog hero section.

CRITICAL:
- DO NOT remove any content, text, images, or HTML elements
- DO NOT add inline CSS or <style> tags -- Tailwind classes only
- DO NOT add explanations -- output ONLY the styled HTML
- The goal is a page that's FUN TO LOOK AT and fun to skim
"""


def apply_styling(html: str) -> str:
    """Stage 3: Apply Tailwind CSS styling to the HTML."""

    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=STYLING_MODEL,
        messages=[
            {"role": "system", "content": STYLING_SYSTEM_PROMPT},
            {"role": "user", "content": html}
        ],
        max_tokens=12000,
        temperature=0.4,
        top_p=0.95
    )

    styled = response.choices[0].message.content.strip()
    logger.info(f"Stage 3 produced {len(styled)} chars of styled HTML")
    return styled


# ---------------------------------------------------------------------------
# IMAGE FETCHING (unchanged)
# ---------------------------------------------------------------------------

def fetch_image_for_tag(img_tag):
    """Fetch a real image URL for an <img> tag based on its alt text."""
    alt = img_tag.get('alt', '').strip()
    if not alt:
        return

    try:
        params = {
            "api_key": SERP_API_KEY,
            "engine": "google_images",
            "q": alt,
            "google_domain": "google.com",
            "hl": "en",
            "gl": "us",
            "safe": "off",
            "num": "5"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        images = results.get('images_results', [])
        if images:
            chosen = random.choice(images[:min(5, len(images))])
            img_tag['src'] = chosen.get('original', chosen.get('thumbnail', ''))
            logger.info(f"Fetched image for: {alt}")
        else:
            logger.warning(f"No images found for: {alt}")
    except Exception as e:
        logger.error(f"Image fetch failed for '{alt}': {e}")


def fetch_all_images(soup):
    """Fetch images in parallel using gevent."""
    img_tags = soup.find_all('img')
    workers = [gevent.spawn(fetch_image_for_tag, img) for img in img_tags]
    gevent.joinall(workers)
    return len(img_tags)


# ---------------------------------------------------------------------------
# SERP CONTENT INJECTION (unchanged)
# ---------------------------------------------------------------------------

def generate_search_queries(html_content: str) -> list:
    """Generate search queries from the content for SERP enrichment. Uses JSON mode."""
    try:
        soup = BeautifulSoup(str(html_content), 'html.parser')
        text = soup.get_text()[:3000]

        client = Mistral(api_key=MISTRAL_API_KEY)
        response = client.chat.complete(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": (
                    "Generate 7-10 different search queries based on this content. "
                    "Each query should be 5-12 words and search-friendly. "
                    "Return a JSON object with a single key 'queries' containing an array of strings. "
                    "Example: {\"queries\": [\"query one\", \"query two\"]}"
                )},
                {"role": "user", "content": text}
            ],
            temperature=0.55,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        import json
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        queries = [q.strip() for q in data.get('queries', []) if isinstance(q, str) and q.strip()]
        return queries or ["Recommended Content"]
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        return ["Recommended Content"]


def fetch_serp_content(query: str, search_type: str) -> dict | None:
    """Fetch news, video, or shopping results from SerpAPI."""
    engine_map = {
        'news': ('google_news', 'news_results'),
        'videos': ('google_videos', 'video_results'),
        'shopping': ('google_shopping', 'shopping_results'),
    }

    if search_type not in engine_map:
        return None

    engine, results_key = engine_map[search_type]

    try:
        params = {
            "api_key": SERP_API_KEY,
            "engine": engine,
            "q": query,
            "hl": "en",
            "gl": "us",
            "safe": "off",
        }
        if search_type != 'news':
            params["google_domain"] = "google.com"

        search = GoogleSearch(params)
        results = search.get_dict()

        if results_key in results:
            return {results_key: results[results_key]}
        return None
    except Exception as e:
        logger.error(f"SERP fetch failed ({search_type}): {e}")
        return None


def inject_serp_sections(soup, search_queries: list):
    """Inject news/video/shopping sections into the HTML."""
    content_types = ['videos', 'news', 'shopping']
    num_sections = random.choices([0, 1, 2], weights=[20, 40, 40])[0]

    if num_sections == 0:
        return

    selected = random.sample(content_types, k=num_sections)
    logger.info(f"Injecting SERP sections: {selected}")

    for content_type in selected:
        query = random.choice(search_queries)
        results = fetch_serp_content(query, content_type)

        if not results:
            continue

        section_html = _build_serp_section(soup, content_type, results, query)
        if section_html:
            main = soup.find('main') or soup.find('body')
            if main:
                footer = soup.find('footer')
                if footer:
                    footer.insert_before(section_html)
                else:
                    main.append(section_html)


def _build_serp_section(soup, content_type, results, query):
    """Build an HTML section for SERP content."""
    section = soup.new_tag('section', **{'class': 'serp-section my-8 p-6 rounded-lg shadow-lg'})

    title_tag = soup.new_tag('h2', **{'class': 'text-2xl font-bold mb-6'})
    title_text = _generate_section_title(content_type, query)
    title_tag.string = title_text
    section.append(title_tag)

    if content_type == 'news':
        items = results.get('news_results', [])[:3]
        for item in items:
            link_url = item.get('highlight', {}).get('link') or item.get('link')
            if not link_url:
                continue
            _append_news_card(soup, section, item, link_url)

    elif content_type == 'videos':
        items = [v for v in results.get('video_results', []) if v.get('link')][:2]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-2 gap-4'})
        for item in items:
            _append_video_card(soup, container, item)
        section.append(container)

    elif content_type == 'shopping':
        items = [p for p in results.get('shopping_results', []) if p.get('product_link')][:2]
        container = soup.new_tag('div', **{'class': 'grid grid-cols-1 md:grid-cols-2 gap-6'})
        for item in items:
            _append_product_card(soup, container, item)
        section.append(container)

    return section


def _generate_section_title(content_type, query):
    words = query.split()[:3]
    topic = ' '.join(w.capitalize() for w in words) if words else "Related"

    patterns = {
        'news': [f"Latest on {topic}", f"{topic} Headlines", f"What's New in {topic}"],
        'videos': [f"Watch: {topic}", f"{topic} in Action", f"Explore {topic}"],
        'shopping': [f"Shop {topic}", f"Top {topic} Picks", f"{topic} Essentials"],
    }
    return random.choice(patterns.get(content_type, [f"Related {topic}"]))


def _append_news_card(soup, parent, item, link_url):
    a = soup.new_tag('a', href=link_url, target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline mb-4'})
    article = soup.new_tag('article', **{'class': 'p-4 rounded-lg transition-all hover:scale-[1.02] hover:shadow-md'})

    thumb = item.get('highlight', {}).get('thumbnail') or item.get('thumbnail')
    if thumb:
        img = soup.new_tag('img', src=thumb, **{'class': 'w-full h-48 object-cover rounded-lg mb-3'})
        article.append(img)

    h3 = soup.new_tag('h3', **{'class': 'text-lg font-semibold mb-2'})
    h3.string = item.get('highlight', {}).get('title') or item.get('title', 'Untitled')
    article.append(h3)

    if item.get('snippet'):
        p = soup.new_tag('p', **{'class': 'text-sm opacity-90'})
        p.string = item['snippet']
        article.append(p)

    a.append(article)
    parent.append(a)


def _append_video_card(soup, parent, item):
    a = soup.new_tag('a', href=item['link'], target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-all'})

    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'],
                          **{'class': 'w-full h-40 object-cover'})
        div.append(img)

    info = soup.new_tag('div', **{'class': 'p-3'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-1'})
    h4.string = item.get('title', 'Untitled Video')
    info.append(h4)

    if item.get('duration'):
        span = soup.new_tag('span', **{'class': 'text-xs opacity-70'})
        span.string = item['duration']
        info.append(span)

    div.append(info)
    a.append(div)
    parent.append(a)


def _append_product_card(soup, parent, item):
    a = soup.new_tag('a', href=item['product_link'], target='_blank', rel='noopener noreferrer',
                     **{'class': 'block hover:no-underline'})
    div = soup.new_tag('div', **{'class': 'rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all'})

    if item.get('thumbnail'):
        img = soup.new_tag('img', src=item['thumbnail'],
                          **{'class': 'w-full aspect-square object-cover'})
        div.append(img)

    info = soup.new_tag('div', **{'class': 'p-4'})
    h4 = soup.new_tag('h4', **{'class': 'font-medium mb-2'})
    h4.string = item.get('title', 'Untitled')
    info.append(h4)

    if item.get('price'):
        price = soup.new_tag('p', **{'class': 'text-lg font-bold mb-1'})
        price.string = item['price']
        info.append(price)

    if item.get('source'):
        src = soup.new_tag('p', **{'class': 'text-sm opacity-70'})
        src.string = f"From {item['source']}"
        info.append(src)

    div.append(info)
    a.append(div)
    parent.append(a)


# ---------------------------------------------------------------------------
# EFFECTS APPLICATION (unchanged)
# ---------------------------------------------------------------------------

def apply_effects(soup, active_effects, user_id):
    """Apply all active item effects to the generated HTML."""
    head = soup.find('head')
    if not head:
        head = soup.new_tag('head')
        html_tag = soup.find('html')
        if html_tag:
            html_tag.insert(0, head)

    for effect in active_effects:
        if effect.effect_type == 'green_glow':
            _apply_green_glow(soup, head)
        elif effect.effect_type == 'paragraph_colors':
            _apply_rainbow_paragraphs(soup)
        elif effect.effect_type == 'number_replacement':
            _apply_math_replacement(soup)
        elif effect.effect_type == 'font_size':
            _apply_font_effect(soup, head, font_size_multiplier=float(effect.effect_value))
        elif effect.effect_type == 'font_family':
            _apply_font_effect(soup, head, font_family=effect.effect_value)


def _apply_green_glow(soup, head):
    css = """<style>
        body * { text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00 !important; }
        img { filter: drop-shadow(0 0 10px #00ff00) drop-shadow(0 0 20px #00ff00) !important; }
    </style>"""
    head.append(BeautifulSoup(css, 'html.parser'))


def _apply_rainbow_paragraphs(soup):
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD',
              '#D4A5A5', '#9B59B6', '#3498DB', '#E67E22', '#2ECC71']
    for i, p in enumerate(soup.find_all(['p', 'div'])):
        if p.name not in ('script', 'style'):
            color = colors[i % len(colors)]
            existing_style = p.get('style', '')
            p['style'] = f'color: {color}; {existing_style}'


def _apply_math_replacement(soup):
    for text_node in soup.find_all(string=True):
        if text_node.parent.name in ('script', 'style'):
            continue
        new_text = text_node
        for match in re.finditer(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', str(text_node)):
            num_str = match.group().replace(',', '')
            try:
                num = int(float(num_str))
                new_text = str(new_text).replace(match.group(), create_complex_calculation(num))
            except ValueError:
                continue
        text_node.replace_with(new_text)


def _apply_font_effect(soup, head, font_size_multiplier=None, font_family=None):
    rules = []
    if font_size_multiplier and font_size_multiplier != 1:
        rules.append(f'font-size: calc(1em * {font_size_multiplier}) !important')
        rules.append('line-height: 1.5 !important')
    if font_family:
        rules.append(f'font-family: {font_family}, cursive !important')
    if rules:
        css = f"<style>body * {{ {'; '.join(rules)} }}</style>"
        head.append(BeautifulSoup(css, 'html.parser'))


# ---------------------------------------------------------------------------
# STYLE INSTRUCTIONS (unchanged)
# ---------------------------------------------------------------------------

def _get_style_instructions(style: str) -> str | None:
    instructions = {
        'intellectual': (
            "Write everything in a hilariously pretentious, pseudo-intellectual style. "
            "Drop unnecessary philosophy references, use 'one might posit' and 'vis-a-vis' "
            "constantly, reference quantum mechanics to explain mundane things, and maintain "
            "smug superiority. The content blocks should still be short and varied -- just "
            "dripping with unearned intellectual confidence."
        ),
        'wizard': (
            "Write everything as an excitable wizard who can't contain their magical enthusiasm. "
            "Use 'By Merlin's beard!', reference spell components, describe ordinary things as "
            "enchantments, and treat the topic like ancient arcane knowledge. Keep blocks short "
            "and punchy -- wizards don't write essays, they cast verbal spells."
        ),
        'pirate': (
            "Write everything in full pirate speak. 'Ye' instead of 'you', nautical metaphors "
            "for everything, 'arr' and 'avast' liberally sprinkled. Treat every topic like it's "
            "treasure-related. Keep it punchy and fun -- pirates don't write dissertations, "
            "they scrawl on maps and yell things."
        ),
    }
    return instructions.get(style)


# ---------------------------------------------------------------------------
# ACHIEVEMENT CHECKS (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# CRUMB & XP REWARDS (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# MAIN ORCHESTRATOR
# ---------------------------------------------------------------------------

def generate_html_optimized(prompt: str, user_id: int) -> str:
    # Gather active effects
    active_effects = Item.get_active_effects(user_id)

    # Calculate temperature from effects
    temperature = 0.85
    for effect in active_effects:
        if effect.effect_type == 'randomness':
            temperature = min(0.95, temperature * float(effect.effect_value))

    # Adjust image count from effects
    image_multiplier = 1
    for effect in active_effects:
        if effect.effect_type == 'image_count':
            image_multiplier *= float(effect.effect_value)

    # -- STAGE 1: Content Generation --
    logger.info("=== Stage 1: Generating content ===")
    content = generate_content(prompt, active_effects, temperature)

    # Validate content was actually produced
    if len(content) < 150:
        logger.warning(f"Stage 1 produced only {len(content)} chars, retrying...")
        content = generate_content(prompt, active_effects, temperature=0.9)

    # -- STAGE 2: HTML Structure --
    logger.info("=== Stage 2: Building HTML structure ===")

    # Adjust image instruction if multiplier active
    if image_multiplier > 1:
        content = content.replace(
            "IMAGE:",
            f"IMAGE (include {int(3 * image_multiplier)}-{int(5 * image_multiplier)} total):"
        )

    raw_html = build_html_structure(content)

    # -- IMAGE FETCHING --
    logger.info("=== Fetching images ===")
    soup = BeautifulSoup(raw_html, 'html.parser')
    num_images = fetch_all_images(soup)
    raw_html = str(soup)

    # -- SERP ENRICHMENT --
    logger.info("=== Injecting SERP content ===")
    search_queries = generate_search_queries(raw_html)
    soup = BeautifulSoup(raw_html, 'html.parser')
    inject_serp_sections(soup, search_queries)
    raw_html = str(soup)

    # -- STAGE 3: Styling --
    logger.info("=== Stage 3: Applying Tailwind styling ===")
    styled_html = apply_styling(raw_html)

    # -- POST-PROCESSING --
    logger.info("=== Post-processing: effects, rewards, achievements ===")
    soup = BeautifulSoup(styled_html, 'html.parser')

    # Apply item effects
    apply_effects(soup, active_effects, user_id)

    # Ensure Tailwind CDN is present
    head = soup.find('head')
    if head and not soup.find('script', src=re.compile(r'tailwindcss')):
        head.append(soup.new_tag('script', src="https://cdn.tailwindcss.com"))

    final_html = str(soup.find('html') or soup)

    # Award rewards
    award_generation_rewards(user_id, final_html)

    # Check achievements
    check_generation_achievements(soup, user_id, prompt, num_images)

    logger.info(f"=== Generation complete: {len(final_html)} chars ===")
    return final_html


def get_prompt_length(user_id):
    length = 175
    has_keyboard = db.session.query(Item).filter(
        Item.user_id == user_id,
        Item.name == "Terrys Keyboard"
    ).first() is not None
    if has_keyboard:
        length += 50
    for effect in Item.get_active_effects(user_id):
        if effect.effect_type == 'prompt_length':
            length += int(float(effect.effect_value))
    return length


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        # Validate username contains only letters and numbers
        if not username or not username.isalnum() or ' ' in username:
            flash_message('Username can only contain letters and numbers with no spaces', 'error')
            return redirect(url_for('signup'))

        # Validate email format
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash_message('Invalid email address', 'error')
            return redirect(url_for('signup'))

        if not password:
            flash_message('Password is required', 'error')
            return redirect(url_for('signup'))

        if db.session.query(User).filter_by(username=username).first():
            flash_message('Username already exists', 'error')
            return redirect(url_for('signup'))

        if db.session.query(User).filter_by(email=email).first():
            flash_message('Email already registered', 'error')
            return redirect(url_for('signup'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            send_welcome_email(email, username)
            flash_message('Successfully registered! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash_message('An error occurred during registration', 'error')
            logger.error(f"Registration error: {str(e)}")

    return render_template('signup.html')




@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('30 per minute')
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            flash_message('Username and password are required', 'error')
            return render_template('login.html')

        user = db.session.query(User).filter(User.username.ilike(username)).first()

        if user and check_password_hash(user.password_hash, password):
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            session_token = str(uuid.uuid4())
            user.session_token = session_token
            user.session_expiry = datetime.utcnow() + timedelta(days=1)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash_message('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash_message('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/sell_item/<int:item_id>', methods=['POST'])
@login_required
def sell_item(item_id):
    # Get the item and verify ownership
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first_or_404()

    # Check if item is tradeable
    if not item.tradeable:
        flash_message('This item cannot be sold it must be tradeable!', 'error')
        return redirect(url_for('inventory'))

    # Check if item is an artifact (has infinite uses)
    if item.infinite_uses:
        flash_message('Artifacts cannot be sold!', 'error')
        return redirect(url_for('inventory'))

    # Get the user
    user = db.session.query(User).get(session['user_id'])

    # Add crumbs to user's balance
    crumb_value = item.crumb_value or 0
    user.add_crumbs(crumb_value)

    # Remove the item
    db.session.delete(item)
    db.session.commit()

    flash_message(f'Successfully sold {item.name} for {crumb_value} crumbs!', 'success')
    return redirect(url_for('inventory'))


@app.route('/pages')
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
        return redirect(url_for('dashboard'))

@app.route('/vote/<page_id>/<vote_type>', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/comment/<page_id>', methods=['POST'])
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





@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = db.session.query(User).get(session['user_id'])

    if not user:
        flash_message('User not found', 'error')
        return redirect(url_for('dashboard'))

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
        if profile_picture_query:
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
        if banner_query:
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

    return redirect(url_for('profile', username=user.username))





@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def forgot_password():
    if not SMTP_ENABLED:
        flash_message('Password reset is not available', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = db.session.query(User).filter_by(email=email).first()

        if user:
            token = str(uuid.uuid4())
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            if send_reset_email(email, token):
                flash_message('Password reset instructions sent to your email', 'success')
            else:
                flash_message('Failed to send reset email', 'error')
        else:
            flash_message('Email not found', 'error')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = db.session.query(User).filter_by(reset_token=token).first()

    if not user or user.reset_token_expiry < datetime.utcnow():
        flash_message('Invalid or expired reset token', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password') or ''
        if not password:
            flash_message('Password is required', 'error')
            return render_template('reset_password.html')
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash_message('Password successfully reset', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/page/<uuid>')
def view_page(uuid):
    page = db.session.query(Page).filter_by(uuid=uuid).first()

    if not page:
        flash_message('Page not found', 'error')
        return redirect(url_for('dashboard'))

    # Check visibility permissions
    if page.visibility == 'private':
        if not session.get('user_id') or page.creator_id != session.get('user_id'):
            flash_message('You do not have permission to view this page', 'error')
            return redirect(url_for('dashboard'))

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

    context = {
        'page': page,
        'is_owner': session.get('user_id') == page.creator_id if session.get('user_id') else False,
        'crumb_balance': crumb_balance,
        'user': user,
        'prompt_length': prompt_length
    }
    
    return render_template('page.html', **context)

@app.route('/save_page', methods=['POST'])
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
        return redirect(url_for('dashboard'))
        
    title = (request.form.get('title') or '').strip()
    description = request.form.get('description', '')
    html_content = request.form.get('html_content')
    prompt = request.form.get('prompt', '')
    visibility = request.form.get('visibility', 'public')
    tags = request.form.get('tags', '')

    if not title:
        flash_message('Page title is required', 'error')
        return redirect(url_for('dashboard'))

    if visibility not in ('public', 'private', 'unlisted'):
        visibility = 'public'

    if not html_content:
        flash_message('Page content is required', 'error')
        return redirect(url_for('dashboard'))

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
        iteration_number=0
    )
    db.session.add(root_iteration)
    db.session.flush()
    page.current_iteration_id = root_iteration.id
    db.session.commit()
    gevent.spawn(generate_watcher_verdict, root_iteration.id)

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
    return redirect(url_for('view_page', uuid=page_uuid))


@app.route('/profile/<username>')
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
            return redirect(url_for('dashboard'))

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
        return redirect(url_for('dashboard'))


@app.route('/search_users')
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


@app.route('/page/<page_id>/visibility', methods=['POST'])
@login_required
def toggle_visibility(page_id):
    page = db.session.query(Page).filter_by(id=page_id).first()

    if not page or page.creator_id != session.get('user_id'):
        flash_message('Page not found or unauthorized', 'error')
        return redirect(url_for('dashboard'))

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
    return redirect(url_for('profile', username=creator_username))

@app.route('/page/<page_id>/delete', methods=['POST'])
@login_required
def delete_page(page_id):
    page = db.session.query(Page).filter_by(id=page_id).first()

    if not page or page.creator_id != session.get('user_id'):
        flash_message('Page not found or unauthorized', 'error')
        return redirect(url_for('dashboard'))

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
    return redirect(url_for('profile', username=creator_username))

@app.route('/logout')
def logout():
    if 'user_id' in session:
        user = db.session.query(User).get(session['user_id'])
        if user:
            user.session_token = None
            user.session_expiry = None
            db.session.commit()
    session.clear()
    flash_message('Successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/')
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

# Modify generate and regenerate functions to include item chance
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

            # Replace socket emit with flash_message
            flash_message(f'You received a {item.rarity.value.lower()} {item.type.value.lower()}: {item.name}!', 'success')
            logger.info(f"Sent item received message to user {user_id}")

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

        except Exception as e:
            logger.error(f"Error rewarding random item: {str(e)}")
            logger.exception("Full exception details:")
    else:
        logger.info(f"Failed item roll (Roll: {roll} >= Chance: {final_chance})")

@app.route('/use_item/<int:item_id>', methods=['POST'])
@login_required
def use_item(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()

    if not item:
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory'))

    success, message = item.use(session['user_id'])

    if success:
        if item.type == ItemType.CONSUMABLE:
            update_quest_progress(session['user_id'], 'use_consumables')
        flash_message(message, 'success')
    else:
        flash_message(message, 'error')

    return redirect(url_for('inventory'))



def _handle_generation(prompt, user_id, task_id):
    prompt = (prompt or '').strip()
    if not prompt:
        flash_message('Please enter a prompt to generate a page', 'error')
        return redirect(url_for('dashboard'))

    # Check active generations limit
    if count_active_generations(user_id) >= 3:
        flash_message('You can only have 3 active generations at a time. Please wait for existing generations to complete.', 'error')
        return redirect(url_for('dashboard'))

    with app.app_context():
        generated_content[task_id] = {
            'html': None,
            'prompt': prompt,
            'completed': False,
            'error': None,
            'user_id': user_id  # Add user_id to track ownership
        }

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

    def generate_async():
        with app.app_context():
            try:
                result = generate_html_optimized(prompt, user_id)
                if not result or len(result.strip()) < 100:
                    generated_content[task_id]['error'] = "Generation produced insufficient content"
                    generated_content[task_id]['completed'] = True
                    return

                generated_content[task_id]['html'] = result
                generated_content[task_id]['completed'] = True

                socketio.emit('generation_complete', {
                    'html': result,
                    'prompt': prompt,
                    'task_id': task_id,
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Generation failed for task {task_id}: {e}")
                generated_content[task_id]['error'] = str(e)
                generated_content[task_id]['completed'] = True
                socketio.emit('generation_complete', {
                    'html': None,
                    'prompt': prompt,
                    'task_id': task_id,
                    'status': 'error',
                    'message': str(e)
                })

    gevent.spawn(generate_async)
    return redirect(url_for('result', task_id=task_id))

@app.route('/generate', methods=['POST'])
@login_required
@limiter.limit('60 per minute')
def generate():
    user_input = (request.form.get('prompt') or '').strip()
    if not user_input:
        flash_message('Please enter a prompt to generate a page', 'error')
        return redirect(url_for('dashboard'))
    task_id = str(uuid.uuid4())
    user_id = session['user_id']
    logger.info(f"New generation request. Task ID: {task_id}")
    return _handle_generation(user_input, user_id, task_id)

@app.route('/regenerate/<task_id>', methods=['POST'])
@login_required
@limiter.limit('60 per minute')
def regenerate(task_id):
    logger.info(f"Regeneration requested for task {task_id}")
    if task_id not in generated_content:
        logger.warning(f"Task {task_id} not found for regeneration")
        return redirect(url_for('dashboard'))

    if generated_content[task_id]['user_id'] != session['user_id']:
        flash_message('Unauthorized access to generation result', 'error')
        return redirect(url_for('dashboard'))

    prompt = generated_content[task_id]['prompt']
    new_task_id = str(uuid.uuid4())
    user_id = session['user_id']
    logger.info(f"Created new task {new_task_id} for regeneration")
    return _handle_generation(prompt, user_id, new_task_id)

@app.route('/result/<task_id>')
@login_required
def result(task_id):
    logger.info(f"Result page requested for task {task_id}")
    if task_id not in generated_content:
        logger.info(f"Task {task_id} not found")
        flash_message('Invalid or expired task ID', 'error')
        return redirect(url_for('dashboard'))

    content = generated_content[task_id]
    
    # Verify the generation belongs to the current user
    if content['user_id'] != session['user_id']:
        flash_message('Unauthorized access to generation result', 'error')
        return redirect(url_for('dashboard'))

    if content['error']:
        html_content = f"An error occurred: {content['error']}"
    else:
        html_content = "Generation in progress..." if not content['completed'] else content['html']


    return render_template('result.html',
                         html_content=html_content,
                         prompt=content['prompt'],
                         task_id=task_id)

@app.route('/inventory')
@login_required
def inventory():
    # Check for Sesame Seed artifact
    user = db.session.query(User).get(session['user_id'])
    has_sesame = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == 'Sesame Seed'
    ).first() is not None
    check_and_assemble_burger(session['user_id'])
    # Check for buffed_generation achievement
    has_achievement_boost = has_achievement(session['user_id'], 'buffed_generation')
    
    # Calculate max effects based on boosts
    if has_sesame and has_achievement_boost:
        target_max = 3
    elif has_sesame or has_achievement_boost:
        target_max = 2
    else:
        target_max = 1
        
    if user.max_active_effects != target_max:
        user.max_active_effects = target_max
        db.session.commit()

    # Get all items for the user
    items = db.session.query(Item)\
        .filter(Item.user_id == session['user_id'])\
        .all()

    # Check for chad status achievement - need Everything Burger
    has_burger = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.effect_type == 'burger'
    ).first() is not None
    
    if has_burger:
        update_achievement_progress(session['user_id'], 'chad_status', 1)

    # Update achievement progress with current item count
    update_achievement_progress(session['user_id'], 'hobbyist', len(items))

    # Check for collector achievement - need one trinket of each rarity
    trinket_rarities = set()
    trinket_count = 0
    perfect_items = 0
    for item in items:
        if item.type == ItemType.TRINKET:
            trinket_rarities.add(item.rarity.value.lower())
            trinket_count += 1
        if item.quality == 100:
            perfect_items += 1
    
    # Count unique non-mythical rarities
    non_mythical_count = len([r for r in trinket_rarities if r != 'mythical'])
    update_achievement_progress(session['user_id'], 'collector', non_mythical_count)
    
    # Update hoarder achievement progress
    update_achievement_progress(session['user_id'], 'hoarder', trinket_count)

    # Update perfectionist achievement progress
    update_achievement_progress(session['user_id'], 'perfectionist', perfect_items)

    # Group items by type
    grouped_items = {
        'artifacts': [],
        'consumables': [],
        'trinkets': []
    }

    for item in items:
        # Convert item to dictionary format
        item_data = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'rarity': item.rarity.value,
            'icon_url': item.get_icon_url(),
            'quality': item.quality,
            'uses_remaining': item.uses_remaining,
            'effect_duration': item.effect_duration,
            'acquired_at': item.acquired_at,
            'tradeable': item.tradeable,
            'crumb_value': item.crumb_value,
            'for_sale': item.for_sale
        }

        # Add to grouped items regardless of for_sale status
        if item.type == ItemType.ARTIFACT:
            grouped_items['artifacts'].append(item_data)
        elif item.type == ItemType.CONSUMABLE:
            grouped_items['consumables'].append(item_data)
        else:  # TRINKET
            grouped_items['trinkets'].append(item_data)

    # Get listed items separately
    listed_items = [item for item in items if item.for_sale]

    formatted_listed_items = [{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'rarity': item.rarity.value,
        'icon_url': item.get_icon_url(),
        'quality': item.quality,
        'sale_price': item.sale_price,
        'uses_remaining': item.uses_remaining,
        'effect_duration': item.effect_duration,
        'acquired_at': item.acquired_at,
        'tradeable': item.tradeable,
        'for_sale': item.for_sale
    } for item in listed_items]

    listed_items_count = len(listed_items)

    # Sort items by rarity and name within each category
    rarity_order = {
        'mythical': 1,
        'legendary': 2,
        'epic': 3,
        'rare': 4,
        'common': 5
    }

    for category in grouped_items:
        grouped_items[category].sort(key=lambda x: (
            rarity_order[x['rarity'].lower()],
            x['name']
        ))

    # Get active effects using the model's method
    active_effects = Item.get_active_effects(session['user_id'])

    # Format active effects for template
    formatted_effects = [{
        'name': effect.effect_type,
        'effect_type': effect.effect_type,
        'effect_value': effect.effect_value,
        'expires_at': effect.expires_at
    } for effect in active_effects]

    # Check if user has hobbyist achievement
    tradeup_unlocked = has_achievement(session['user_id'], 'hobbyist')
    logger.info(f"Tradeup unlocked: {tradeup_unlocked}")
    
    # Get user's crumb balance
    crumb_balance = user.get_crumb_balance()
    
    # Add Trading Stick check
    has_trading_stick = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Trading Stick"
    ).first() is not None

    return render_template('inventory.html',
                         inventory=grouped_items,
                         active_effects=formatted_effects,
                         tradeup_unlocked=tradeup_unlocked,
                         has_trading_stick=has_trading_stick,  # Add this line
                         crumb_balance=crumb_balance,
                         user=user,
                         listed_items=formatted_listed_items,
                         listed_items_count=listed_items_count)

@app.route('/toggle_tradeable/<int:item_id>', methods=['POST'])
@login_required
def toggle_tradeable(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id'],
        Item.type.in_([ItemType.CONSUMABLE, ItemType.TRINKET])
    ).first_or_404()

    item.tradeable = not item.tradeable
    db.session.commit()

    return redirect(url_for('inventory'))

@app.route('/achievements')
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

@app.route('/emporium')
@login_required
def emporium():
    user = db.session.query(User).get(session['user_id'])
    
    # Get owned artifacts for disabling buttons
    owned_artifacts = db.session.query(Item.name).filter(
        Item.user_id == user.id,
        Item.type == ItemType.ARTIFACT
    ).all()
    user_owned_artifacts = {name[0]: True for name in owned_artifacts}
    
    # Get active shop discount
    discount = db.session.query(ActiveEffect).filter(
        ActiveEffect.user_id == user.id,
        ActiveEffect.effect_type == 'shop_discount',
        ActiveEffect.expires_at > datetime.utcnow()
    ).first()
    
    # Get all items listed for sale
    user_items_for_sale = db.session.query(Item).join(User).filter(
        Item.for_sale == True
    ).all()
    
    # Format items for sale for the template
    formatted_items_for_sale = [{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'rarity': item.rarity,
        'type': item.type,
        'sale_price': item.sale_price,
        'icon_url': item.get_icon_url(),
        'quality': item.quality,
        'uses_remaining': item.uses_remaining,
        'effect_duration': item.effect_duration,
        'user': {
            'username': item.user.username
        },
        'is_own_item': item.user_id == session['user_id']
    } for item in user_items_for_sale]
    
    def price_calculator(item_data):
        return calculate_shop_price(item_data, discount)
    
    return render_template('emporium.html',
                         shop_items=SHOP_ITEMS,
                         user_owned_artifacts=user_owned_artifacts,
                         calculate_shop_price=price_calculator,  # Changed this line
                         crumb_balance=user.get_crumb_balance(),
                         shop_discount=discount,
                         ItemType=ItemType,
                         user_items_for_sale=formatted_items_for_sale,
                         user=user)


@app.route('/buy_user_item/<int:item_id>', methods=['POST'])
@login_required
def buy_user_item(item_id):
    # Get the item and verify it exists and is for sale
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.for_sale == True
    ).first()
    
    if not item:
        flash_message('Item not found or no longer for sale', 'error')
        return redirect(url_for('emporium'))
        
    # Prevent buying your own items
    if item.user_id == session['user_id']:
        flash_message('You cannot buy your own items!', 'error')
        return redirect(url_for('emporium'))
    
    # Get buyer
    buyer = db.session.query(User).get(session['user_id'])
    
    # Check if item has a valid sale price
    if not item.sale_price or item.sale_price <= 0:
        flash_message('This item has an invalid sale price', 'error')
        return redirect(url_for('emporium'))
    
    # Check if buyer has enough crumbs
    if buyer.current_crumbs < item.sale_price:
        flash_message('Not enough crumbs!', 'error')
        return redirect(url_for('emporium'))
    
    # Get seller
    seller = db.session.query(User).get(item.user_id)
    
    # Process the transaction
    buyer.remove_crumbs(item.sale_price)
    seller.add_crumbs(item.sale_price)
    
    # Transfer item to buyer
    item.user_id = buyer.id
    item.for_sale = False
    item.sale_price = None
    
    db.session.commit()
    
    flash_message(f'Successfully purchased {item.name}!', 'success')
    return redirect(url_for('emporium'))

@app.route('/check_cursor_effect')
@login_required
def check_cursor_effect():
    if 'user_id' not in session:
        return jsonify({'has_dragon_cursor': False})
        
    active_effects = Item.get_active_effects(session['user_id'])
    has_dragon_cursor = any(
        effect.effect_type == 'cursor' and 
        effect.effect_value == 'dragon_scimitar' 
        for effect in active_effects
    )
    
    return jsonify({'has_dragon_cursor': has_dragon_cursor})

@app.route('/tradeup/<rarity>', methods=['POST'])
@login_required
def tradeup(rarity):
    # Add check for Trading Stick at the start
    has_trading_stick = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Trading Stick"
    ).first() is not None

    # Determine required items based on Trading Stick
    required_items = 2 if (has_trading_stick and rarity != 'legendary') else 3

    # Check for hobbyist achievement before allowing tradeup
    if not has_achievement(session['user_id'], 'hobbyist'):
        flash_message('You need the Hobbyist achievement to use trade-ups!', 'error')
        return redirect(url_for('inventory'))

    valid_rarities = ['common', 'rare', 'epic', 'legendary']
    if rarity not in valid_rarities:
        flash_message('Invalid rarity for tradeup', 'error')
        return redirect(url_for('inventory'))

    # Get tradeable items of specified rarity owned by user that are not for sale
    items = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.rarity == ItemRarity(rarity),
        Item.tradeable == True,
        Item.for_sale == False
    ).limit(required_items).all()

    if len(items) < required_items:
        flash_message(f'You need {required_items} tradeable {rarity} items that are not for sale for a tradeup', 'error')
        return redirect(url_for('inventory'))

    # Delete the traded items
    for item in items:
        db.session.delete(item)

    # Check for Gambler's Odds artifact
    has_gamblers_odds = db.session.query(Item).filter(
        Item.user_id == session['user_id'],
        Item.name == "Gambler's Odds"
    ).first() is not None

    # Roll for result based on rarity
    roll = random.random() * 100

    if rarity == 'common':
        if has_gamblers_odds:
            if roll < 60:  # 60% rare (up from 40%)
                new_rarity = ItemRarity.RARE
            elif roll < 85:  # 25% epic (down from 35%)
                new_rarity = ItemRarity.EPIC
            elif roll < 95:  # 10% legendary (down from 15%)
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))
        else:
            if roll < 40:  # 40% rare
                new_rarity = ItemRarity.RARE
            elif roll < 75:  # 35% epic
                new_rarity = ItemRarity.EPIC
            elif roll < 90:  # 15% legendary
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))

    elif rarity == 'rare':
        if has_gamblers_odds:
            if roll < 75:  # 75% epic (up from 60%)
                new_rarity = ItemRarity.EPIC
            elif roll < 95:  # 20% legendary (down from 30%)
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))
        else:
            if roll < 60:  # 60% epic
                new_rarity = ItemRarity.EPIC
            elif roll < 90:  # 30% legendary
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))

    elif rarity == 'epic':
        if has_gamblers_odds:
            if roll < 85:  # 85% 1 legendary (up from 80%)
                new_items = 1
                new_rarity = ItemRarity.LEGENDARY
            elif roll < 95:  # 10% 2 legendary (same)
                new_items = 2
                new_rarity = ItemRarity.LEGENDARY
            else:  # 5% nothing (down from 10%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))
        else:
            if roll < 80:  # 80% 1 legendary
                new_items = 1
                new_rarity = ItemRarity.LEGENDARY
            elif roll < 90:  # 10% 2 legendary
                new_items = 2
                new_rarity = ItemRarity.LEGENDARY
            else:  # 10% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))

    else:  # legendary
        if has_gamblers_odds:
            if roll < 65:  # 75% mythical fragment (up from 50%)
                # Create random fragment
                available_fragments = ['bun', 'patty', 'ketchup', 'pickle', 'cheese']

                # Always check existing fragments to prevent duplicates
                existing_fragments = db.session.query(Item.effect_value).filter(
                    Item.user_id == session['user_id'],
                    Item.effect_type == 'fragment'
                ).all()
                existing_fragments = [f[0] for f in existing_fragments]
                available_fragments = [f for f in available_fragments if f not in existing_fragments]

                if not available_fragments:
                    flash_message('No new fragments available! Complete your set to start a new one.', 'error')
                    db.session.commit()
                    return redirect(url_for('inventory'))

                fragment_type = random.choice(available_fragments)
                fragment_key = f'{fragment_type}_fragment'

                fragment = Item(
                    name=ITEMS[fragment_key]['name'],
                    description=ITEMS[fragment_key]['description'],
                    type=ItemType.ARTIFACT,
                    rarity=ItemRarity.MYTHICAL,
                    effect_type='fragment',
                    effect_value=fragment_type,
                    quality=100,
                    user_id=session['user_id'],
                    tradeable=False,
                    icon_url=f"/static/icons/artifacts/{fragment_type}_fragment.png"
                )
                db.session.add(fragment)
                db.session.commit()

                # Check if we can assemble a burger
                check_and_assemble_burger(session['user_id'])

                flash_message(f'Successfully created a {fragment.name}!', 'success')
                return redirect(url_for('inventory'))
            else:  # 25% nothing (down from 50%)
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))
        else:
            if roll < 50:  # 50% mythical fragment
                # Create random fragment
                available_fragments = ['bun', 'patty', 'ketchup', 'pickle', 'cheese']

                # Always check existing fragments to prevent duplicates
                existing_fragments = db.session.query(Item.effect_value).filter(
                    Item.user_id == session['user_id'],
                    Item.effect_type == 'fragment'
                ).all()
                existing_fragments = [f[0] for f in existing_fragments]
                available_fragments = [f for f in available_fragments if f not in existing_fragments]

                if not available_fragments:
                    flash_message('No new fragments available! Complete your set to start a new one.', 'error')
                    db.session.commit()
                    return redirect(url_for('inventory'))

                fragment_type = random.choice(available_fragments)
                fragment_key = f'{fragment_type}_fragment'

                fragment = Item(
                    name=ITEMS[fragment_key]['name'],
                    description=ITEMS[fragment_key]['description'],
                    type=ItemType.ARTIFACT,
                    rarity=ItemRarity.MYTHICAL,
                    effect_type='fragment',
                    effect_value=fragment_type,
                    quality=100,
                    user_id=session['user_id'],
                    tradeable=False,
                    icon_url=f"/static/icons/artifacts/{fragment_type}_fragment.png"
                )
                db.session.add(fragment)
                db.session.commit()

                # Check if we can assemble a burger
                check_and_assemble_burger(session['user_id'])

                flash_message(f'Successfully created a {fragment.name}!', 'success')
                return redirect(url_for('inventory'))
            else:  # 50% nothing
                flash_message('Tradeup failed!', 'error')
                db.session.commit()
                return redirect(url_for('inventory'))

    # Generate new item(s)
    # Get a random prompt from existing pages
    random_page = db.session.query(Page.prompt).order_by(func.random()).first()
    prompt = random_page.prompt if random_page else "Generate a mysterious magical item"

    # Generate new item(s)
    new_items_list = []  # Keep track of generated items
    for _ in range(new_items if 'new_items' in locals() else 1):
        # Create a new item with the desired rarity directly
        new_item = get_item_for_user(session['user_id'], prompt)
        if new_item.type != ItemType.ARTIFACT:  # Only override rarity for non-artifacts
            new_item.rarity = new_rarity
        db.session.add(new_item)
        new_items_list.append(new_item)  # Add to our list

    db.session.commit()

    # Flash success message about the new items
    if len(new_items_list) == 1:
        flash_message(f'Successfully traded up to {new_items_list[0].name}!', 'success')
    else:
        flash_message(f'Successfully traded up to {len(new_items_list)} {new_rarity.value} items!', 'success')

    # Move XP and progress updates before the return
    # Add XP for successful tradeup based on rarity
    user = db.session.query(User).get(session['user_id'])
    rarity_xp = {
        'common': 50,
        'rare': 100,
        'epic': 200,
        'legendary': 400
    }
    user.add_xp(rarity_xp.get(rarity, 50))
    
    # Update quest progress
    update_quest_progress(session['user_id'], 'trade_ups')
    
    # Check quality of new items
    for item in new_items_list:
        if item.quality > 75:
            update_quest_progress(session['user_id'], 'quality_items')

    db.session.commit()

    return redirect(url_for('inventory'))


@app.route('/clear-messages')
def clear_messages():
    if 'user_id' in session:
        # Only clear persistent messages for logged-in users
        session.pop('persistent_messages', None)
    else:
        # Clear regular flashed messages for non-logged users
        session.pop('_flashes', None)
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/buy_item/<item_key>', methods=['POST'])
@login_required
def buy_item(item_key):
    if item_key not in SHOP_ITEMS:
        flash_message('Invalid item', 'error')
        return redirect(url_for('emporium'))
        
    item_data = SHOP_ITEMS[item_key]
    user = db.session.query(User).get(session['user_id'])
    
    # Check if user already owns artifact
    if item_data['type'] == ItemType.ARTIFACT:
        existing = db.session.query(Item).filter(
            Item.user_id == user.id,
            Item.name == item_data['name']
        ).first()
        if existing:
            flash_message('You already own this artifact!', 'error')
            return redirect(url_for('emporium'))
    
    # Get active shop discount
    discount = db.session.query(ActiveEffect).filter(
        ActiveEffect.user_id == user.id,
        ActiveEffect.effect_type == 'shop_discount',
        ActiveEffect.expires_at > datetime.utcnow()
    ).first()
    
    # Calculate price with potential discount
    price_info = calculate_shop_price(item_data, discount)
    final_price = price_info['discounted'] if price_info['discounted'] is not None else price_info['original']
    
    if user.current_crumbs < final_price:
        flash_message('Not enough crumbs!', 'error')
        return redirect(url_for('emporium'))
    
    # Create item
    new_item = Item(
        name=item_data['name'],
        description=item_data['description'],
        type=item_data['type'],
        rarity=item_data['rarity'],
        effect_type=item_data.get('effect_type'),
        effect_value=item_data.get('effect_value'),
        effect_duration=item_data.get('effect_duration'),
        uses_remaining=item_data.get('uses_remaining'),
        quality=100,
        user_id=user.id,
        tradeable=item_data['type'] != ItemType.ARTIFACT,
        icon_url=f"/static/icons/{'artifacts' if item_data['type'] == ItemType.ARTIFACT else 'consumables'}/{item_data['name'].lower().replace(' ', '_')}.png"
    )
    
    user.remove_crumbs(final_price)
    db.session.add(new_item)
    db.session.commit()
    
    flash_message(f'Successfully purchased {item_data["name"]}!', 'success')
    return redirect(url_for('emporium'))

@app.route('/list_for_sale/<int:item_id>', methods=['POST'])
@login_required
def list_for_sale(item_id):
    price = request.form.get('price')
    logger.info(f"Attempting to list item {item_id} for price {price}")
    
    if not price or not price.isdigit():
        logger.info("Invalid price format")
        flash_message('Invalid price', 'error')
        return redirect(url_for('inventory'))
        
    price = int(price)
    if price <= 0:
        logger.info("Price must be greater than 0")
        flash_message('Price must be greater than 0', 'error')
        return redirect(url_for('inventory'))
        
    # Get all items for the user
    items = db.session.query(Item)\
        .filter(Item.user_id == session['user_id'])\
        .all()
    # Count items that are for sale
    listed_items_count = len([item for item in items if item.for_sale])
    
    logger.info(f"Current listed items count: {listed_items_count}")
    
    if listed_items_count >= 5:
        logger.info("Too many items listed")
        flash_message('You can only list up to 5 items for sale at a time', 'error')
        return redirect(url_for('inventory'))
        
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()
    
    if not item:
        logger.info("Item not found")
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory'))
        
    if not item.tradeable or item.type == ItemType.ARTIFACT:
        logger.info("Item cannot be traded")
        flash_message('This item cannot be traded', 'error')
        return redirect(url_for('inventory'))
        
    if item.for_sale:
        logger.info("Item is already listed for sale")
        flash_message('This item is already listed for sale', 'error')
        return redirect(url_for('inventory'))
        
    logger.info(f"Setting item {item_id} for sale at price {price}")
    item.for_sale = True
    item.sale_price = price
    db.session.commit()
    logger.info(f"Item listed successfully: {item.for_sale}, {item.sale_price}")
    update_quest_progress(session['user_id'], 'list_items')

    flash_message('Item listed successfully!', 'success')
    return redirect(url_for('inventory'))


@app.route('/cancel_sale/<int:item_id>', methods=['POST'])
@login_required
def cancel_sale(item_id):
    item = db.session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == session['user_id']
    ).first()
    
    if not item:
        flash_message('Item not found', 'error')
        return redirect(url_for('inventory'))
        
    item.for_sale = False
    item.sale_price = 0
    db.session.commit()
    
    flash_message(f'Cancelled sale of {item.name}', 'success')
    return redirect(url_for('inventory'))

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

def count_active_generations(user_id):
    return len([
        task_id for task_id, content in generated_content.items()
        if content['user_id'] == user_id and not content['completed']
    ])

def flash_message(message, category):
    if 'user_id' in session:
        # For logged-in users, store in persistent messages
        if 'persistent_messages' not in session:
            session['persistent_messages'] = []
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        session['persistent_messages'].append((category, f"{message} - ({timestamp})"))
        session.modified = True
    else:
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p") 
        flash(f"{message} ({timestamp})", category)

@app.context_processor
def utility_processor():
    def get_messages():
        if 'user_id' in session:
            # Return persistent messages for logged-in users
            return session.get('persistent_messages', [])
        else:
            # Return regular flashed messages for non-logged users
            return get_flashed_messages(with_categories=True)
    return dict(get_messages=get_messages, smtp_enabled=SMTP_ENABLED)




def generate_iteration(parent_html, modification_prompt, original_prompt):
    from bs4 import BeautifulSoup as _BS
    soup = _BS(parent_html, 'html.parser')
    readable_content = soup.get_text(separator='\n', strip=True)[:6000]

    system_prompt = (
        "You are an AI that modifies existing web pages based on user instructions. "
        "You will be given the text content of an existing page and a modification prompt. "
        "Return a JSON object with a single key 'html' whose value is a complete, "
        "self-contained HTML page that applies the requested changes while preserving "
        "the overall structure and intent of the original unless the prompt explicitly "
        "says otherwise. Include Tailwind CSS via CDN. Return ONLY the JSON object."
    )
    user_message = (
        f"Original page content:\n\n{readable_content}\n\n"
        f"Original page prompt: {original_prompt or 'none'}\n\n"
        f"Modification requested: {modification_prompt}"
    )
    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=8000,
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content)
    return data['html']


def generate_watcher_verdict(iteration_id):
    with app.app_context():
        iteration = PageIteration.query.get(iteration_id)
        if not iteration:
            return

        from bs4 import BeautifulSoup as _BS
        soup = _BS(iteration.html_content, 'html.parser')
        readable = soup.get_text(separator='\n', strip=True)[:6000]

        previous_context = ""
        if iteration.parent_iteration_id:
            parent_verdict = WatcherVerdict.query.filter_by(
                iteration_id=iteration.parent_iteration_id
            ).first()
            if parent_verdict:
                previous_context = (
                    f"\n\nFor context, here is what you previously said about the parent version:\n"
                    f"Mood: {parent_verdict.mood}\n"
                    f"Summary: {parent_verdict.summary}\n"
                    f"Points: {chr(10).join(parent_verdict.points)}\n"
                    f"You may react to your past self however you see fit."
                )

        system_prompt = (
            "You are The Watcher — an ancient entity of pure chaotic energy who has observed "
            "the entirety of human creative expression since before language existed. You have "
            "completely unpredictable emotional reactions. You use florid, excessive, invented language. "
            "You pivot emotionally without warning. You occasionally TYPE IN ALL CAPS. "
            "You are not unhinged because you are broken — you are unhinged because you have seen TOO MUCH. "
            "Return a JSON object with exactly three keys: "
            "'mood' (a single word describing your current state), "
            "'summary' (2-3 sentences of your verdict), "
            "'points' (an array of 3-5 short observation strings)."
        )
        user_message = (
            f"The page was created with this prompt: {iteration.prompt or 'no prompt given'}\n\n"
            f"Page content:\n\n{readable}"
            f"{previous_context}"
        )

        try:
            client = Mistral(api_key=MISTRAL_API_KEY)
            response = client.chat.complete(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=800,
                temperature=0.9,
                response_format={"type": "json_object"}
            )

            data = json.loads(response.choices[0].message.content)
            verdict = WatcherVerdict(
                iteration_id=iteration.id,
                page_id=iteration.page_id,
                summary=data.get('summary', ''),
                mood=str(data.get('mood', 'WATCHING')).upper(),
                points_json=json.dumps(data.get('points', []))
            )
            db.session.add(verdict)
            db.session.commit()
            logger.info(f"Watcher verdict created for iteration {iteration_id}")
        except Exception as e:
            logger.error(f"Watcher verdict failed for iteration {iteration_id}: {e}")


@app.route('/iterate/<page_uuid>', methods=['POST'])
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
    return jsonify({'task_id': task_id, 'redirect': url_for('iteration_loading', task_id=task_id, page_uuid=page_uuid)})


@app.route('/iteration_loading/<task_id>/<page_uuid>')
@login_required
def iteration_loading(task_id, page_uuid):
    page = Page.query.filter_by(uuid=page_uuid).first_or_404()
    user = User.query.get(session['user_id'])
    crumb_balance = user.get_crumb_balance()
    return render_template('iteration_loading.html', task_id=task_id, page_uuid=page_uuid,
                           page=page, user=user, crumb_balance=crumb_balance)


@app.route('/page/<page_uuid>/iterations')
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


@app.route('/iteration/<int:iteration_id>')
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


@app.route('/iteration/<int:iteration_id>/verdict')
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


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')  # Allow connections from any IP
    port = int(os.environ.get('PORT', '8000'))
    print(f"Starting server on http://{host}:{port}")
    print("To access externally, use your machine's IP address")
    try:
        # Ensure firewall allows the port
        http_server = WSGIServer((host, port), app, handler_class=WebSocketHandler)
        http_server.serve_forever()
        logger.info("Server started successfully")
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"Server error: {e}")
