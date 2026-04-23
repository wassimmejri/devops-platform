import requests
from os import getenv
from datetime import datetime, timedelta

LOKI_URL  = getenv('LOKI_URL')
LOKI_HOST = getenv('LOKI_HOST')   # ← "loki.devops.local"

HEADERS = {'Host': LOKI_HOST} if LOKI_HOST else {}   # ← header Host forcé

def get_logs(pod_name, namespace, limit=100):
    query = f'{{namespace="{namespace}", pod="{pod_name}"}}'
    end   = datetime.utcnow()
    start = end - timedelta(hours=1)

    url = f"{LOKI_URL}/loki/api/v1/query_range"
    response = requests.get(url, params={
        'query':     query,
        'limit':     limit,
        'start':     int(start.timestamp() * 1e9),
        'end':       int(end.timestamp()   * 1e9),
        'direction': 'backward',
    }, headers=HEADERS, timeout=10)   # ← ajouter headers=HEADERS
    return response.json()

def get_namespace_logs(namespace, limit=200):
    query = f'{{namespace="{namespace}"}}'
    end   = datetime.utcnow()
    start = end - timedelta(hours=1)

    url = f"{LOKI_URL}/loki/api/v1/query_range"
    response = requests.get(url, params={
        'query':     query,
        'limit':     limit,
        'start':     int(start.timestamp() * 1e9),
        'end':       int(end.timestamp()   * 1e9),
        'direction': 'backward',
    }, headers=HEADERS, timeout=10)   # ← ajouter headers=HEADERS
    return response.json()