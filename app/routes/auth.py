import re
import uuid
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import limiter
from app.models import db, User
from app.config import SMTP_ENABLED
from app.email import send_reset_email, send_welcome_email
from app.utils import flash_message

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        # Validate username contains only letters and numbers
        if not username or not username.isalnum() or ' ' in username:
            flash_message('Username can only contain letters and numbers with no spaces', 'error')
            return redirect(url_for('auth.signup'))

        # Validate email format
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash_message('Invalid email address', 'error')
            return redirect(url_for('auth.signup'))

        if not password:
            flash_message('Password is required', 'error')
            return redirect(url_for('auth.signup'))

        if db.session.query(User).filter_by(username=username).first():
            flash_message('Username already exists', 'error')
            return redirect(url_for('auth.signup'))

        if db.session.query(User).filter_by(email=email).first():
            flash_message('Email already registered', 'error')
            return redirect(url_for('auth.signup'))

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
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash_message('An error occurred during registration', 'error')
            logger.error(f"Registration error: {str(e)}")

    return render_template('signup.html')




@auth_bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('generation.dashboard'))
        else:
            flash_message('Invalid username or password', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        user = db.session.query(User).get(session['user_id'])
        if user:
            user.session_token = None
            user.session_expiry = None
            db.session.commit()
    session.clear()
    flash_message('Successfully logged out', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def forgot_password():
    if not SMTP_ENABLED:
        flash_message('Password reset is not available', 'error')
        return redirect(url_for('auth.login'))

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

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = db.session.query(User).filter_by(reset_token=token).first()

    if not user or user.reset_token_expiry < datetime.utcnow():
        flash_message('Invalid or expired reset token', 'error')
        return redirect(url_for('auth.login'))

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
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')