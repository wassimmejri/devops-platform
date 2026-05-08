from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required, get_or_create_user
from app.models.project import Project
from app.models.user import User
from app import db
from app.services.keycloak_admin_service import (
    list_users, get_user_roles, update_user_status,
    change_user_role, delete_user, reset_password_email
)

admin_bp = Blueprint('admin', __name__)

def require_admin(user):
    if user.role != 'admin-devops':
        return jsonify({'message': 'Accès réservé aux administrateurs'}), 403
    return None

@admin_bp.route('/users', methods=['GET'])
@keycloak_required
def get_users():
    user = get_or_create_user(request.userinfo)
    err  = require_admin(user)
    if err: return err

    try:
        kc_users = list_users()
        result   = []

        for kc_user in kc_users:
            kc_id  = kc_user.get('id')
            email  = kc_user.get('email', '')
            roles  = get_user_roles(kc_id)
            role_names = [r['name'] for r in roles
                          if r['name'] in ['admin-devops', 'developer']]

            # Infos depuis la DB
            db_user   = User.query.filter_by(email=email).first()
            projects   = Project.query.filter_by(owner_id=db_user.id).all() if db_user else []

            result.append({
                'keycloak_id':  kc_id,
                'email':        email,
                'first_name':   kc_user.get('firstName', ''),
                'last_name':    kc_user.get('lastName', ''),
                'enabled':      kc_user.get('enabled', True),
                'role':         role_names[0] if role_names else 'developer',
                'projects_count': len(projects),
                'created_at':   kc_user.get('createdTimestamp'),
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@admin_bp.route('/users/<keycloak_id>/role', methods=['PUT'])
@keycloak_required
def update_role(keycloak_id):
    user = get_or_create_user(request.userinfo)
    err  = require_admin(user)
    if err: return err

    data     = request.get_json() or {}
    new_role = data.get('role')

    if new_role not in ['admin-devops', 'developer']:
        return jsonify({'message': 'Rôle invalide'}), 400

    try:
        change_user_role(keycloak_id, new_role)

        # Sync DB
        kc_users = list_users()
        kc_user  = next((u for u in kc_users if u['id'] == keycloak_id), None)
        if kc_user:
            db_user = User.query.filter_by(email=kc_user.get('email')).first()
            if db_user:
                db_user.role = new_role
                db.session.commit()

        return jsonify({'message': 'Rôle mis à jour avec succès'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@admin_bp.route('/users/<keycloak_id>/status', methods=['PUT'])
@keycloak_required
def update_status(keycloak_id):
    user = get_or_create_user(request.userinfo)
    err  = require_admin(user)
    if err: return err

    data    = request.get_json() or {}
    enabled = data.get('enabled', True)

    try:
        update_user_status(keycloak_id, enabled)
        return jsonify({'message': f"Utilisateur {'activé' if enabled else 'suspendu'}"}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@admin_bp.route('/users/<keycloak_id>', methods=['DELETE'])
@keycloak_required
def remove_user(keycloak_id):
    user = get_or_create_user(request.userinfo)
    err  = require_admin(user)
    if err: return err

    try:
        kc_users = list_users()
        kc_user  = next((u for u in kc_users if u['id'] == keycloak_id), None)

        delete_user(keycloak_id)

        # Supprime aussi de la DB
        if kc_user:
            db_user = User.query.filter_by(email=kc_user.get('email')).first()
            if db_user:
                db.session.delete(db_user)
                db.session.commit()

        return jsonify({'message': 'Utilisateur supprimé'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@admin_bp.route('/users/<keycloak_id>/reset-password', methods=['POST'])
@keycloak_required
def reset_password(keycloak_id):
    user = get_or_create_user(request.userinfo)
    err  = require_admin(user)
    if err: return err

    try:
        reset_password_email(keycloak_id)
        return jsonify({'message': 'Email de réinitialisation envoyé'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500