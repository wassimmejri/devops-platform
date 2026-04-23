import eventlet
eventlet.monkey_patch()          # ← DOIT être en toute première ligne

from dotenv import load_dotenv
from app import create_app, socketio

load_dotenv(override=True)
app = create_app()

if __name__ == '__main__':
    print('[SERVER] Starting Flask app with SocketIO')
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,         # ← False obligatoire avec eventlet
        use_reloader=False,
        log_output=True
    )