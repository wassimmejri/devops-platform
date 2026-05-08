from flask import Blueprint, jsonify, request
from app.utils.auth_decorator import keycloak_required, role_required
from app.services.alertmanager_service import get_alerts, get_alert_groups, silence_alert

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/', methods=['GET'])
@keycloak_required
def list_alerts():
    try:
        return jsonify(get_alerts()), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@alerts_bp.route('/groups', methods=['GET'])
@keycloak_required
def list_alert_groups():
    try:
        return jsonify(get_alert_groups()), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# ── Silence — admin-devops uniquement ────────────────
@alerts_bp.route('/silence', methods=['POST'])
@keycloak_required
@role_required('admin-devops')
def create_silence():
    try:
        data       = request.json
        result     = silence_alert(
            data.get('matchers', []),
            data.get('createdBy', 'devops-platform'),
            data.get('comment', ''),
            data.get('startsAt'),
            data.get('endsAt')
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500