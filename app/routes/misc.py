from flask import Blueprint, request, redirect, url_for, session

misc_bp = Blueprint('misc', __name__)

@misc_bp.route('/clear-messages')
def clear_messages():
    if 'user_id' in session:
        # Only clear persistent messages for logged-in users
        session.pop('persistent_messages', None)
    else:
        # Clear regular flashed messages for non-logged users
        session.pop('_flashes', None)
    
    return redirect(request.referrer or url_for('generation.dashboard'))