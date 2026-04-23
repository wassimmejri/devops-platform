from flask import Blueprint, jsonify, request
from app.utils.auth_decorator import keycloak_required
from app.services.alertmanager_service import get_alerts, get_alert_groups, silence_alert

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/', methods=['GET'])
@keycloak_required
def list_alerts():
    try:
        alerts = get_alerts()
        return jsonify(alerts), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@alerts_bp.route('/groups', methods=['GET'])
@keycloak_required
def list_alert_groups():
    try:
        groups = get_alert_groups()
        return jsonify(groups), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@alerts_bp.route('/silence', methods=['POST'])
@keycloak_required
def create_silence():
    try:
        data       = request.json
        matchers   = data.get('matchers', [])
        created_by = data.get('createdBy', 'devops-platform')
        comment    = data.get('comment', '')
        starts_at  = data.get('startsAt')
        ends_at    = data.get('endsAt')
        result = silence_alert(matchers, created_by, comment, starts_at, ends_at)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500