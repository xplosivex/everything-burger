from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_migrate import Migrate
from app.models import db

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent', transport='websocket')
migrate = Migrate()
