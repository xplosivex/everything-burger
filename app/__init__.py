import os
import logging
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, get_flashed_messages

from app.config import SECRET_KEY, SMTP_ENABLED
from app.extensions import db, csrf, limiter, socketio, migrate
from app.utils import flash_message
from app import models  # noqa: F401  (register models with SQLAlchemy)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

request_logger = logging.getLogger('werkzeug')
request_logger.setLevel(logging.INFO)


def create_app():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, template_folder=os.path.join(root, 'templates'),
                static_folder=os.path.join(root, 'static'))

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
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='gevent', transport='websocket')

    # Ensure all tables are created
    with app.app_context():
        db.create_all()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.pages import pages_bp
    from app.routes.profile import profile_bp
    from app.routes.generation import generation_bp
    from app.routes.inventory import inventory_bp
    from app.routes.emporium import emporium_bp
    from app.routes.achievements import achievements_bp
    from app.routes.iterations import iterations_bp
    from app.routes.misc import misc_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(generation_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(emporium_bp)
    app.register_blueprint(achievements_bp)
    app.register_blueprint(iterations_bp)
    app.register_blueprint(misc_bp)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash_message("You're moving a little fast — try again in a moment.", "error")
        return redirect(request.referrer or url_for('dashboard'))

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

    return app
