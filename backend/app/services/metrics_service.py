import requests
from os import getenv
import time


PROMETHEUS_URL = getenv('PROMETHEUS_URL')
PROMETHEUS_HOST = getenv('PROMETHEUS_HOST')

def get_metric(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    headers = {'Host': PROMETHEUS_HOST} if PROMETHEUS_HOST else {}
    response = requests.get(url, params={'query': query}, 
                            headers=headers, timeout=5)
    return response.json()

def get_history_metrics(minutes=5, step=30):
    if not PROMETHEUS_URL:
        return {'cpu': [], 'ram': []}
    headers = {'Host': PROMETHEUS_HOST} if PROMETHEUS_HOST else {}
    end = int(time.time())
    start = end - minutes * 60

    query_cpu = f'sum(rate(node_cpu_seconds_total{{mode!="idle"}}[1m])) by (instance) * 100'
    query_ram = f'avg((1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)'

    def do_range_query(query):
        url = f"{PROMETHEUS_URL}/api/v1/query_range"
        params = {'query': query, 'start': start, 'end': end, 'step': f'{step}s'}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get('data', {}).get('result', [])
                if not data:
                    return []
                # On moyenne toutes les instances à chaque timestamp
                timestamps = set()
                for series in data:
                    for v in series.get('values', []):
                        timestamps.add(int(v[0]))
                timestamps = sorted(timestamps)
                sums = {t: 0.0 for t in timestamps}
                counts = {t: 0 for t in timestamps}
                for series in data:
                    for v in series.get('values', []):
                        t = int(v[0])
                        sums[t] += float(v[1])
                        counts[t] += 1
                points = [[t, sums[t] / counts[t]] for t in timestamps]
                return points
        except Exception as e:
            print(f"[History] Erreur prom: {e}")
        return []

    cpu_points = do_range_query(query_cpu)
    ram_points = do_range_query(query_ram)
    return {'cpu': cpu_points, 'ram': ram_points}