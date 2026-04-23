import requests
from requests.auth import HTTPBasicAuth
from os import getenv

JENKINS_URL = getenv('JENKINS_URL')
JENKINS_USER = getenv('JENKINS_USER')
JENKINS_TOKEN = getenv('JENKINS_TOKEN')

def trigger_job(job_name, params=None):
    url = f"{JENKINS_URL}/job/{job_name}/buildWithParameters"
    response = requests.post(url, auth=HTTPBasicAuth(JENKINS_USER, JENKINS_TOKEN), params=params)
    return response.status_code

def get_job_status(job_name, build_number):
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/api/json"
    response = requests.get(url, auth=HTTPBasicAuth(JENKINS_USER, JENKINS_TOKEN))
    return response.json() if response.status_code == 200 else {}