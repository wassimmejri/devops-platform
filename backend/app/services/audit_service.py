from app import db
from app.models.audit import AuditLog
from flask import request as flask_request
from datetime import datetime

def log_action(
    user_email: str,
    action: str,
    resource: str   = None,
    detail: str     = None,
    status: str     = 'success',
    user_role: str  = None,
    ip_address: str = None
):
    """Enregistre une action dans l'audit log."""
    try:
        # Récupère l'IP automatiquement si pas fournie
        if not ip_address:
            ip_address = flask_request.headers.get(
                'X-Forwarded-For',
                flask_request.remote_addr
            )

        entry = AuditLog(
            timestamp  = datetime.utcnow(),
            user_email = user_email,
            user_role  = user_role,
            action     = action,
            resource   = resource,
            detail     = detail,
            status     = status,
            ip_address = ip_address
        )
        db.session.add(entry)
        db.session.commit()
        print(f"[AUDIT] {user_email} → {action} → {resource} → {status}")
    except Exception as e:
        print(f"[AUDIT ERROR] {str(e)}")
        db.session.rollback()


# ── Actions constantes ────────────────────────────────────
class AuditAction:
    # Auth
    LOGIN              = 'LOGIN'
    LOGOUT             = 'LOGOUT'
    LOGIN_FAILED       = 'LOGIN_FAILED'

    # Projets
    PROJECT_CREATE     = 'PROJECT_CREATE'
    PROJECT_DELETE     = 'PROJECT_DELETE'

    # Microservices
    MICROSERVICE_CREATE  = 'MICROSERVICE_CREATE'
    MICROSERVICE_DELETE  = 'MICROSERVICE_DELETE'
    MICROSERVICE_DEPLOY  = 'MICROSERVICE_DEPLOY'
    DEPLOY_SUCCESS       = 'DEPLOY_SUCCESS'
    DEPLOY_FAILED        = 'DEPLOY_FAILED'

    # Administration
    USER_ROLE_CHANGE   = 'USER_ROLE_CHANGE'
    USER_SUSPEND       = 'USER_SUSPEND'
    USER_ACTIVATE      = 'USER_ACTIVATE'
    USER_DELETE        = 'USER_DELETE'
    USER_RESET_PASSWORD = 'USER_RESET_PASSWORD'

    # Cluster
    POD_RESTART        = 'POD_RESTART'