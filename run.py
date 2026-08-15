import os
import sys
import logging
from waitress import serve

from app import create_app
from app.worker import start_workers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup profile selection.
#
# Choose how many users you expect to serve and run.py sizes the request
# thread pool, background worker pool, and SQLAlchemy connection pool to
# match. The goal is to give waitress enough threads to keep every user's
# request moving without oversubscribing the box.
#
#   profile 1  (small)    ~  up to 25 concurrent users
#   profile 2  (medium)   ~  up to 150 concurrent users
#   profile 3  (large)    ~  up to 1000 concurrent users
#
# Pick at startup by passing it as the first CLI argument or by setting
# EB2_PROFILE in the environment:
#
#   python run.py 1
#   python run.py 2
#   python run.py 3
#   EB2_PROFILE=2 python run.py
#
# Defaults to profile 2 if nothing is given.
# ---------------------------------------------------------------------------

PROFILES = {
    1: {
        'name': 'small',
        'waitress_threads': 8,
        'bg_workers': 4,
        'db_pool': 5,
        'db_overflow': 5,
    },
    2: {
        'name': 'medium',
        'waitress_threads': 24,
        'bg_workers': 12,
        'db_pool': 15,
        'db_overflow': 10,
    },
    3: {
        'name': 'large',
        'waitress_threads': 80,
        'bg_workers': 32,
        'db_pool': 40,
        'db_overflow': 20,
    },
}


def _resolve_profile():
    # 1) CLI argument: python run.py <1|2|3>
    if len(sys.argv) > 1:
        try:
            value = int(sys.argv[1])
            if value in PROFILES:
                return value
        except ValueError:
            pass
    # 2) Environment variable
    try:
        value = int(os.environ.get('EB2_PROFILE', '0'))
        if value in PROFILES:
            return value
    except ValueError:
        pass
    # 3) Default
    return 2


def main():
    profile_num = _resolve_profile()
    profile = PROFILES[profile_num]

    # Configure SQLAlchemy pool before creating the app. The app factory reads
    # these from the environment so migrations/other entry points stay simple.
    os.environ.setdefault('DB_POOL_SIZE', str(profile['db_pool']))
    os.environ.setdefault('DB_MAX_OVERFLOW', str(profile['db_overflow']))

    app = create_app()

    # Start the embedded queue workers. Jobs (page generation, iteration
    # rewrites, watcher verdicts) are pushed onto Redis by the web app and
    # consumed here, so work survives restarts and doesn't block requests.
    _, _workers = start_workers(app, profile['bg_workers'])

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8000'))

    print("=" * 60)
    print(f"  EVERYTHING BURGER 2")
    print(f"  Profile: {profile_num} ({profile['name']})")
    print(f"  Request threads : {profile['waitress_threads']}")
    print(f"  Queue workers   : {profile['bg_workers']}")
    print(f"  DB pool         : {profile['db_pool']} (+{profile['db_overflow']})")
    print(f"  Redis           : {os.environ.get('REDIS_URL', 'redis://localhost:6379/0')}")
    print(f"  Listening on    : http://{host}:{port}")
    print("=" * 60)

    # socketio.init_app wraps the Flask app in SocketIO's WSGI middleware, so
    # serving app.wsgi_app through waitress handles both HTTP and Socket.IO
    # traffic (long-polling; waitress does not support the websocket upgrade).
    serve(app.wsgi_app,
          host=host,
          port=port,
          threads=profile['waitress_threads'],
          channel_timeout=3600,
          max_request_body_size=64 * 1024 * 1024)  # 64 MB for large page HTML


if __name__ == '__main__':
    main()
