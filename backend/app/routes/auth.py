from flask import Blueprint, request, jsonify
from app.services.keycloak_service import get_token, verify_token, refresh_token, logout
from app.utils.auth_decorator import keycloak_required, get_or_create_user
from app import db
from app.models.user import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)


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

    userinfo = verify_token(token_data['access_token'])

    if userinfo:
        # 👇 Corrections : exploiter les rôles extraits par verify_token
        roles = userinfo.get('roles', [])
        if 'admin-devops' in roles:
            role = 'admin-devops'
        else:
            role = 'developer'

        # Synchroniser l'utilisateur en base (optionnel, mais utile)
        from app.utils.auth_decorator import get_or_create_user
        user = get_or_create_user(userinfo)
        # Le rôle en base sera écrasé par la fonction get_or_create_user si elle est bien codée

        return jsonify({
            'access_token':  token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in':    token_data['expires_in'],
            'user': {
                'username':  userinfo.get('preferred_username', username),
                'email':     userinfo.get('email', ''),
                'full_name': userinfo.get('name', username),
                'role':      role,          # ← désormais correct
                'roles':     roles,         # ← liste complète
            }
        }), 200

    # Fallback (si verify_token échoue)
    return jsonify({
        'access_token':  token_data['access_token'],
        'refresh_token': token_data['refresh_token'],
        'expires_in':    token_data['expires_in'],
        'user': {
            'username': username,
            'email': '',
            'full_name': username,
            'role': 'developer',
            'roles': []
        }
    }), 200


# ── Refresh token ────────────────────────────────────
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data  = request.get_json()
    token = data.get('refresh_token')
    if not token:
        return jsonify({'message': 'Refresh token manquant'}), 400

    new_token = refresh_token(token)
    if not new_token:
        return jsonify({'message': 'Refresh token invalide'}), 401

    # ← AJOUT : vérifier le nouveau token pour extraire les rôles
    userinfo = verify_token(new_token['access_token'])
    
    user_data = {}
    if userinfo:
        roles = userinfo.get('roles', [])
        role  = 'admin-devops' if 'admin-devops' in roles else 'developer'
        user  = get_or_create_user(userinfo)
        user_data = {
            'username':  userinfo.get('preferred_username', ''),
            'email':     userinfo.get('email', ''),
            'full_name': userinfo.get('name', ''),
            'role':      role,
            'roles':     roles,
        }

    return jsonify({
        'access_token':  new_token['access_token'],
        'refresh_token': new_token.get('refresh_token', token),
        'expires_in':    new_token['expires_in'],
        'user':          user_data    # ← AJOUT
    }), 200


# ── Logout ───────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
def logout_route():
    data  = request.get_json()
    token = data.get('refresh_token')
    if token:
        logout(token)
    return jsonify({'message': 'Déconnecté avec succès'}), 200


# ── Get current user ─────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@keycloak_required
def me():
    user  = get_or_create_user(request.userinfo)
    roles = request.user_roles   # extrait par keycloak_required
    return jsonify({
        'email':     user.email,
        'full_name': user.full_name,
        'role':      user.role,
        'roles':     roles,
    }), 200