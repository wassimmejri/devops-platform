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

        request.userinfo   = userinfo
        request.user_email = userinfo.get('email', '')

        # ✅ verify_token retourne déjà 'roles' directement
        request.user_roles = userinfo.get('roles', [])
        return f(*args, **kwargs)
    return decorated


def role_required(*required_roles):
    """
    Décorateur qui vérifie que l'utilisateur a au moins un des rôles requis.
    Usage :
        @keycloak_required
        @role_required('admin-devops')
        def my_route(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_roles = getattr(request, 'user_roles', [])
            if not any(role in user_roles for role in required_roles):
                return jsonify({
                    'message': 'Accès refusé — privilèges insuffisants',
                    'required': list(required_roles),
                    'yours':    user_roles
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_or_create_user(userinfo):
    from app import db
    from app.models.user import User

    email = userinfo.get('email', '')
    user  = User.query.filter_by(email=email).first()

    roles = userinfo.get('roles', [])
    print(f"[DEBUG] get_or_create_user email={email} roles={roles}")

    # ← Ne mettre à jour le rôle QUE si Keycloak retourne des rôles explicites
    if 'admin-devops' in roles:
        role = 'admin-devops'
    elif 'developer' in roles:
        role = 'developer'
    else:
        role = None   # ← pas de rôle Keycloak → on ne touche pas au rôle en DB

    if not user:
        user = User(
            email=email,
            full_name=userinfo.get('name', email),
            password='keycloak',
            role=role or 'developer'   # ← fallback uniquement à la création
        )
        db.session.add(user)
        db.session.commit()
    else:
        if role and user.role != role:   # ← mise à jour UNIQUEMENT si rôle non vide
            user.role = role
            db.session.commit()

    return user