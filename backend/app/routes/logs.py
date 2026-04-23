from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required
from app.services.logs_service import get_logs, get_namespace_logs as svc_namespace_logs

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/pods/<namespace>/<pod_name>', methods=['GET'])
@keycloak_required
def get_pod_logs(namespace, pod_name):
    try:
        limit  = int(request.args.get('limit', 100))
        result = get_logs(pod_name, namespace, limit=limit)
        streams = result.get('data', {}).get('result', [])

        logs = []
        for stream in streams:
            for ts, raw_line in stream.get('values', []):
                logs.append({
                    'timestamp': ts,
                    'line':      raw_line,
                    'pod':       stream.get('stream', {}).get('pod', pod_name),
                })
        logs.sort(key=lambda x: x['timestamp'])
        return jsonify({'pod': pod_name, 'namespace': namespace, 'logs': logs}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@logs_bp.route('/namespace/<namespace>', methods=['GET'])
@keycloak_required
def get_namespace_logs(namespace):
    try:
        limit  = int(request.args.get('limit', 200))
        result = svc_namespace_logs(namespace, limit=limit)
        streams = result.get('data', {}).get('result', [])

        logs = []
        for stream in streams:
            for ts, raw_line in stream.get('values', []):
                logs.append({
                    'timestamp': ts,
                    'line':      raw_line,
                    'pod':       stream.get('stream', {}).get('pod', ''),
                })
        logs.sort(key=lambda x: x['timestamp'])
        return jsonify({'namespace': namespace, 'logs': logs}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500