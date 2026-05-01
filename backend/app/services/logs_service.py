import requests
from os import getenv
from datetime import datetime, timezone, timedelta

LOKI_URL  = getenv('LOKI_URL')
LOKI_HOST = getenv('LOKI_HOST')
HEADERS   = {'Host': LOKI_HOST} if LOKI_HOST else {}

def _loki_params(query, limit, hours=24):
    now   = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    return {
        'query':     query,
        'limit':     limit,
        'start':     int(start.timestamp() * 1_000_000_000),  # ← nanosecondes
        'end':       int(now.timestamp()   * 1_000_000_000),  # ← nanosecondes
        'direction': 'backward',
    }

def get_logs(pod_name, namespace, limit=100):
    query = f'{{namespace="{namespace}", pod="{pod_name}"}}'
    print(f'[DEBUG get_logs] query={query}')
    url = f"{LOKI_URL}/loki/api/v1/query_range"
    response = requests.get(url, params=_loki_params(query, limit),
                            headers=HEADERS, timeout=10)
    print(f'[DEBUG get_logs] status={response.status_code}')
    return response.json()

def get_namespace_logs(namespace, limit=200):
    query = f'{{namespace="{namespace}"}}'
    url = f"{LOKI_URL}/loki/api/v1/query_range"
    response = requests.get(url, params=_loki_params(query, limit),
                            headers=HEADERS, timeout=10)
    print(f'[DEBUG get_namespace_logs] status={response.status_code}, ns={namespace}')
    return response.json()