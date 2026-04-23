from functools import wraps
from flask import request, jsonify
from app.services.keycloak_service import verify_token


def keycloak_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Token manquant'}), 401

        token = auth_header.split(' ')[1]
        userinfo = verify_token(token)

        if not userinfo:
            return jsonify({'message': 'Token invalide ou expiré'}), 401

        request.userinfo = userinfo
        request.user_email = userinfo.get('email', '')
        return f(*args, **kwargs)
    return decorated


def get_or_create_user(userinfo):
    from app import db
    from app.models.user import User

    email = userinfo.get('email', '')
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            full_name=userinfo.get('name', email),
            password='keycloak',
            role='developer'
        )
        db.session.add(user)
        db.session.commit()
    return user