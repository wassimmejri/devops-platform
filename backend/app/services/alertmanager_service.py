import requests
from os import getenv

ALERTMANAGER_URL  = getenv('ALERTMANAGER_URL')
ALERTMANAGER_HOST = getenv('ALERTMANAGER_HOST')

HEADERS = {'Host': ALERTMANAGER_HOST} if ALERTMANAGER_HOST else {}

def get_alerts():
    url = f"{ALERTMANAGER_URL}/api/v2/alerts"
    response = requests.get(url, headers=HEADERS, timeout=5)
    return response.json()

def get_alert_groups():
    url = f"{ALERTMANAGER_URL}/api/v2/alerts/groups"
    response = requests.get(url, headers=HEADERS, timeout=5)
    return response.json()

def silence_alert(matchers, created_by, comment, starts_at, ends_at):
    url = f"{ALERTMANAGER_URL}/api/v2/silences"
    payload = {
        "matchers":  matchers,
        "startsAt":  starts_at,
        "endsAt":    ends_at,
        "createdBy": created_by,
        "comment":   comment,
    }
    response = requests.post(url, json=payload, headers=HEADERS, timeout=5)
    return response.json()