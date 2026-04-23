from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required
from kubernetes import client, config
import os

k8s_bp = Blueprint('k8s', __name__)

def get_k8s_client():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config(os.getenv('K8S_CONFIG_PATH', '~/.kube/config'))
    return client.CoreV1Api(), client.AppsV1Api()

@k8s_bp.route('/pods/<namespace>', methods=['GET'])
@keycloak_required
def get_pods(namespace):
    try:
        core_v1, _ = get_k8s_client()
        pods = core_v1.list_namespaced_pod(namespace=namespace)
        result = []
        for pod in pods.items:
            result.append({
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'ready': all(c.ready for c in (pod.status.container_statuses or [])),
                'restarts': sum(c.restart_count for c in (pod.status.container_statuses or [])),
                'node': pod.spec.node_name,
                'ip': pod.status.pod_ip,
                'created_at': str(pod.metadata.creation_timestamp)
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@k8s_bp.route('/pods', methods=['GET'])
@keycloak_required
def get_all_pods():
    try:
        core_v1, _ = get_k8s_client()
        pods = core_v1.list_pod_for_all_namespaces()
        result = []
        for pod in pods.items:
            result.append({
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'ready': all(c.ready for c in (pod.status.container_statuses or [])),
                'restarts': sum(c.restart_count for c in (pod.status.container_statuses or [])),
                'node': pod.spec.node_name,
                'ip': pod.status.pod_ip,
                'created_at': str(pod.metadata.creation_timestamp)
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@k8s_bp.route('/pods/<namespace>/<pod_name>/logs', methods=['GET'])
@keycloak_required
def get_pod_logs(namespace, pod_name):
    try:
        core_v1, _ = get_k8s_client()
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=100
        )
        return jsonify({'pod': pod_name, 'namespace': namespace, 'logs': logs}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@k8s_bp.route('/pods/<namespace>/<pod_name>/restart', methods=['POST'])
@keycloak_required
def restart_pod(namespace, pod_name):
    try:
        core_v1, _ = get_k8s_client()
        core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return jsonify({'message': f'Pod {pod_name} redémarré avec succès'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@k8s_bp.route('/deployments/<namespace>/<deployment_name>/scale', methods=['POST'])
@keycloak_required
def scale_deployment(namespace, deployment_name):
    try:
        data = request.get_json()
        replicas = data.get('replicas', 1)
        _, apps_v1 = get_k8s_client()
        apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body={'spec': {'replicas': replicas}}
        )
        return jsonify({'message': f'Déploiement {deployment_name} scalé à {replicas} replicas'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@k8s_bp.route('/deployments/<namespace>', methods=['GET'])
@keycloak_required
def get_deployments(namespace):
    try:
        _, apps_v1 = get_k8s_client()
        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        result = []
        for d in deployments.items:
            result.append({
                'name': d.metadata.name,
                'namespace': d.metadata.namespace,
                'replicas': d.spec.replicas,
                'ready_replicas': d.status.ready_replicas or 0,
                'available_replicas': d.status.available_replicas or 0,
                'created_at': str(d.metadata.creation_timestamp)
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
@k8s_bp.route('/nodes', methods=['GET'])
@keycloak_required
def get_nodes():
    try:
        core_v1, _ = get_k8s_client()
        nodes = core_v1.list_node()
        result = []
        for node in nodes.items:
            conditions = {c.type: c.status for c in node.status.conditions}
            # Récupérer l'adresse IP interne
            internal_ip = None
            for addr in node.status.addresses or []:
                if addr.type == 'InternalIP':
                    internal_ip = addr.address
                    break
            result.append({
                'name': node.metadata.name,
                'status': 'Ready' if conditions.get('Ready') == 'True' else 'NotReady',
                'roles': [
                    k.replace('node-role.kubernetes.io/', '')
                    for k in node.metadata.labels.keys()
                    if 'node-role.kubernetes.io/' in k
                ],
                'cpu': node.status.capacity.get('cpu'),
                'memory': node.status.capacity.get('memory'),
                'os': node.status.node_info.os_image,
                'kernel': node.status.node_info.kernel_version,
                'container_runtime': node.status.node_info.container_runtime_version,
                'ip': internal_ip   # <-- NOUVEAU
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500