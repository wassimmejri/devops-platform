from flask import Blueprint, request, jsonify
from app.services.keycloak_service import get_token, verify_token, refresh_token, logout
from app import db
from app.models.user import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# ── Decorator pour protéger les routes ──────────────
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
        return f(*args, **kwargs)
    return decorated


# ── Login via Keycloak ───────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username') or data.get('email', '').split('@')[0]
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username et password obligatoires'}), 400

    token_data = get_token(username, password)

    if not token_data:
        return jsonify({'message': 'Identifiants incorrects'}), 401

    # Essayer de récupérer les infos utilisateur
    userinfo = verify_token(token_data['access_token'])

    # Synchroniser l'utilisateur dans notre DB si userinfo disponible
    if userinfo:
        email = userinfo.get('email', '')
        if email:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=userinfo.get('name', username),
                    password='keycloak',
                    role='developer'
                )
                db.session.add(user)
                db.session.commit()

        return jsonify({
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data['expires_in'],
            'user': {
                'username': userinfo.get('preferred_username', username),
                'email': userinfo.get('email', ''),
                'full_name': userinfo.get('name', username)
            }
        }), 200

    # Si userinfo échoue, retourne quand même le token
    return jsonify({
        'access_token': token_data['access_token'],
        'refresh_token': token_data['refresh_token'],
        'expires_in': token_data['expires_in'],
        'user': {
            'username': username,
            'email': '',
            'full_name': username
        }
    }), 200


# ── Refresh token ────────────────────────────────────
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json()
    token = data.get('refresh_token')

    if not token:
        return jsonify({'message': 'Refresh token manquant'}), 400

    new_token = refresh_token(token)
    if not new_token:
        return jsonify({'message': 'Refresh token invalide'}), 401

    return jsonify({
        'access_token': new_token['access_token'],
        'refresh_token': new_token['refresh_token'],
        'expires_in': new_token['expires_in']
    }), 200


# ── Logout ───────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
def logout_route():
    data = request.get_json()
    token = data.get('refresh_token')

    if token:
        logout(token)

    return jsonify({'message': 'Déconnecté avec succès'}), 200


# ── Get current user ─────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@keycloak_required
def me():
    return jsonify(request.userinfo), 200