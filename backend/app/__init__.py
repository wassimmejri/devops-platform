from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")  # +async_mode


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    CORS(app)

    # Routes
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.microservices import microservices_bp
    from app.routes.k8s import k8s_bp
    from app.routes.jenkins import jenkins_bp
    from app.routes.metrics import metrics_bp
    from app.routes.logs import logs_bp
    from app.routes.alerts import alerts_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(microservices_bp, url_prefix='/api/projects')
    app.register_blueprint(k8s_bp, url_prefix='/api/k8s')
    app.register_blueprint(jenkins_bp, url_prefix='/api/jenkins')
    app.register_blueprint(metrics_bp, url_prefix='/api/metrics')
    app.register_blueprint(logs_bp, url_prefix='/api/logs')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')


    # Sockets                          ← AJOUT
    from app.sockets import register_sockets
    register_sockets(socketio)

    with app.app_context():
        db.create_all()

    return app