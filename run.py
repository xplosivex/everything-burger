from gevent import monkey
monkey.patch_all()

import os
import logging
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from app import create_app
from app.extensions import socketio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

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
