import requests
from os import getenv

PROMETHEUS_URL = getenv('PROMETHEUS_URL')
PROMETHEUS_HOST = getenv('PROMETHEUS_HOST')

def get_metric(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    headers = {'Host': PROMETHEUS_HOST} if PROMETHEUS_HOST else {}
    response = requests.get(url, params={'query': query}, 
                            headers=headers, timeout=5)
    return response.json()