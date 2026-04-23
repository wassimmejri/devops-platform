from flask import Blueprint, request, jsonify
from app.utils.auth_decorator import keycloak_required
import requests as http_requests
import os

metrics_bp = Blueprint('metrics', __name__)

def get_prometheus_url():
    return os.getenv('PROMETHEUS_URL', 'http://localhost:9090')

def get_prometheus_host():
    return os.getenv('PROMETHEUS_HOST', '')

def prometheus_query(query):
    url = f"{get_prometheus_url()}/api/v1/query"
    headers = {}
    host = get_prometheus_host()
    if host:
        headers['Host'] = host
    response = http_requests.get(
        url,
        params={'query': query},
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        return response.json().get('data', {}).get('result', [])
    return []

@metrics_bp.route('/pods', methods=['GET'])
@keycloak_required
def get_pod_metrics():
    try:
        namespace = request.args.get('namespace', '')
        filter_str = f'namespace="{namespace}"' if namespace else ''

        cpu_results = prometheus_query(
            f'sum(rate(container_cpu_usage_seconds_total{{{filter_str}}}[5m])) by (pod, namespace)'
        )
        ram_results = prometheus_query(
            f'sum(container_memory_usage_bytes{{{filter_str}}}) by (pod, namespace)'
        )

        metrics = {}
        for r in cpu_results:
            pod = r['metric'].get('pod', '')
            ns = r['metric'].get('namespace', '')
            if pod:
                metrics[pod] = {
                    'pod': pod,
                    'namespace': ns,
                    'cpu': round(float(r['value'][1]) * 1000, 2),
                    'ram': 0
                }

        for r in ram_results:
            pod = r['metric'].get('pod', '')
            if pod and pod in metrics:
                metrics[pod]['ram'] = round(float(r['value'][1]) / 1024 / 1024, 2)

        return jsonify(list(metrics.values())), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@metrics_bp.route('/nodes', methods=['GET'])
@keycloak_required
def get_node_metrics():
    try:
        # CPU usage (%)
        cpu_results = prometheus_query(
            'sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance)'
        )
        # RAM usage (%)
        ram_results = prometheus_query(
            '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100'
        )

        result = []
        # Indexer les résultats RAM par instance
        ram_by_instance = {}
        for r in ram_results:
            instance = r['metric'].get('instance', '')
            ram_by_instance[instance] = float(r['value'][1])

        for r in cpu_results:
            instance = r['metric'].get('instance', '')
            cpu_usage = round(float(r['value'][1]) * 100, 1)
            ram_usage = round(ram_by_instance.get(instance, 0), 1)
            result.append({
                'instance': instance,
                'cpu_usage': cpu_usage,
                'ram_usage': ram_usage
            })

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500