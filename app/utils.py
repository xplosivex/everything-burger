import logging
from functools import wraps
from flask import session, redirect, url_for, flash, request, has_request_context

logger = logging.getLogger(__name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Don't flash an error for the site root: hitting / when logged
            # out is the normal landing flow, not a failed page access.
            if request.path != '/':
                flash_message('Please log in to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def flash_message(message, category):
    from datetime import datetime
    # Background workers (e.g. item rewards during iteration) have no request
    # context, so there's no session to write to. Skip silently there.
    if not has_request_context():
        logger.debug(f"Skipping flash_message outside request context: {message}")
        return
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
