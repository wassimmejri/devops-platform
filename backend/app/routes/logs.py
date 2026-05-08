from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required, get_or_create_user
from app.services.logs_service import get_logs, get_namespace_logs as svc_namespace_logs
from app.models.project import Project

logs_bp = Blueprint('logs', __name__)

def user_can_access_namespace(user, namespace):
    """Vérifie si l'user a accès au namespace demandé."""
    if user.role == 'admin-devops':
        return True
    project = Project.query.filter_by(
        k8s_namespace=namespace,
        owner_id=user.id
    ).first()
    return project is not None

@logs_bp.route('/pods/<namespace>/<pod_name>', methods=['GET'])
@keycloak_required
def get_pod_logs(namespace, pod_name):
    user = get_or_create_user(request.userinfo)

    if not user_can_access_namespace(user, namespace):
        return jsonify({'message': 'Accès refusé à ce namespace'}), 403

    try:
        limit   = int(request.args.get('limit', 100))
        result  = get_logs(pod_name, namespace, limit=limit)
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
    user = get_or_create_user(request.userinfo)

    if not user_can_access_namespace(user, namespace):
        return jsonify({'message': 'Accès refusé à ce namespace'}), 403

    try:
        limit   = int(request.args.get('limit', 200))
        result  = svc_namespace_logs(namespace, limit=limit)
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

@logs_bp.route('/namespaces', methods=['GET'])
@keycloak_required
def get_accessible_namespaces():
    user = get_or_create_user(request.userinfo)

    if user.role == 'admin-devops':
        # ✅ Admin voit TOUS les namespaces du cluster Kubernetes
        try:
            from app.services.k8s_service import get_k8s_clients
            _, core_v1 = get_k8s_clients()
            ns_list    = core_v1.list_namespace()
            namespaces = [ns.metadata.name for ns in ns_list.items]
        except Exception as e:
            print(f"[ERROR] list_namespace: {e}")
            # Fallback sur les projets en DB si k8s inaccessible
            projects   = Project.query.all()
            namespaces = [p.k8s_namespace for p in projects if p.k8s_namespace]
    else:
        # Developer voit seulement ses propres namespaces
        projects   = Project.query.filter_by(owner_id=user.id).all()
        namespaces = [p.k8s_namespace for p in projects if p.k8s_namespace]

    return jsonify({'namespaces': sorted(namespaces)}), 200