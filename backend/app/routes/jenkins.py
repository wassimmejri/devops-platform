from flask import Blueprint, request, jsonify, current_app
from app.utils.auth_decorator import keycloak_required, get_or_create_user
from app.models.microservice import Microservice
from app.models.project import Project
from app.models.deployment import Deployment
from app import db
import requests
import os
import xml.sax.saxutils as saxutils
from requests.exceptions import RequestException
import traceback
from datetime import datetime

jenkins_bp = Blueprint('jenkins', __name__)


# ── Helpers ──────────────────────────────────────────

def get_jenkins_url():
    url = current_app.config.get('JENKINS_URL')
    if not url:
        url = os.getenv('JENKINS_URL')
    print(f"[DEBUG] Resolved Jenkins URL: {url}")
    return url

def get_jenkins_host():
    host = current_app.config.get('JENKINS_HOST')
    if not host:
        host = os.getenv('JENKINS_HOST')
    return host

def get_auth():
    user = current_app.config.get('JENKINS_USER') or os.getenv('JENKINS_USER')
    token = current_app.config.get('JENKINS_TOKEN') or os.getenv('JENKINS_TOKEN')
    return (user, token)

def jenkins_get(path):
    headers = {}
    host = get_jenkins_host()
    if host:
        headers['Host'] = host
    url = f"{get_jenkins_url()}{path}"
    print(f"[DEBUG] Jenkins GET {url} headers={headers}")
    try:
        return requests.get(url, auth=get_auth(), headers=headers or None, timeout=10)
    except RequestException as exc:
        print(f"[ERROR] Jenkins GET failed: {exc}")
        raise RuntimeError(f"Jenkins GET failed: {exc}") from exc

def jenkins_post(path, data=None, extra_headers=None):
    headers = {}
    host = get_jenkins_host()
    if host:
        headers['Host'] = host
    if extra_headers:
        headers.update(extra_headers)
    url = f"{get_jenkins_url()}{path}"
    print(f"[DEBUG] Jenkins POST {url} headers={headers} data_length={len(data) if data else 0}")
    try:
        return requests.post(url, auth=get_auth(), headers=headers or None, data=data, timeout=10)
    except RequestException as exc:
        print(f"[ERROR] Jenkins POST failed: {exc}")
        raise RuntimeError(f"Jenkins POST failed: {exc}") from exc

def validate_jenkins_config():
    url = get_jenkins_url()
    user, token = get_auth()
    if not url:
        raise RuntimeError('JENKINS_URL is not set')
    if not user or not token:
        raise RuntimeError('JENKINS_USER or JENKINS_TOKEN is not set')

def get_crumb():
    response = jenkins_get("/crumbIssuer/api/json")
    if response.status_code == 200:
        data = response.json()
        return {data['crumbRequestField']: data['crumb']}
    return {}


# ── Déclencher un déploiement ────────────────────────

@jenkins_bp.route('/microservices/<int:microservice_id>/deploy', methods=['POST'])
@keycloak_required
def deploy(microservice_id):
    user = get_or_create_user(request.userinfo)
    microservice = Microservice.query.join(Project).filter(
        Microservice.id == microservice_id,
        Project.owner_id == user.id
    ).first()
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404
    try:
        print(f"[DEBUG] Deploy request for microservice_id={microservice_id}")
        print(f"[DEBUG] User: {user.email}")
        validate_jenkins_config()
        job_name = microservice.jenkins_job_name
        print(f"[DEBUG] Microservice Jenkins job: {job_name}")
        check = jenkins_get(f"/job/{job_name}/api/json")
        print(f"[DEBUG] Check job status code: {check.status_code}")
        if check.status_code == 404:
            print("[DEBUG] Job introuvable, création en cours...")
            result = _create_jenkins_job(job_name, microservice)
            print(f"[DEBUG] Job creation result: {result}")
            if not result:
                return jsonify({'message': 'Erreur lors de la création du job Jenkins'}), 500
        crumb = get_crumb()
        print(f"[DEBUG] Crumb: {crumb}")
        if not crumb:
            return jsonify({'message': "Impossible d'obtenir le crumb Jenkins"}), 500
        trigger = jenkins_post(f"/job/{job_name}/build", extra_headers=crumb)
        print(f"[DEBUG] Trigger status code: {trigger.status_code}")
        if trigger.status_code not in [200, 201, 302]:
            return jsonify({'message': f'Erreur déclenchement pipeline (status {trigger.status_code})'}), 500
        data = request.get_json() or {}
        deployment = Deployment(
            version=data.get('version', 'latest'),
            status='building',
            microservice_id=microservice_id,
            triggered_by=user.id,
            created_at=datetime.utcnow()
        )
        microservice.status = 'deploying'
        db.session.add(deployment)
        db.session.commit()
        print("[DEBUG] Deployment saved in DB")
        return jsonify({'message': 'Déploiement déclenché avec succès', 'deployment': deployment.to_dict()}), 201
    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR] Exception: {str(e)}")
        return jsonify({'message': 'Erreur interne du serveur', 'detail': str(e)}), 500


# ── Statut du dernier build ──────────────────────────

@jenkins_bp.route('/status/<job_name>', methods=['GET'])
@keycloak_required
def get_job_status(job_name):
    try:
        response = jenkins_get(f"/job/{job_name}/lastBuild/api/json")
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'job_name': job_name,
                'build_number': data.get('number'),
                'result': data.get('result'),
                'building': data.get('building'),
                'duration': data.get('duration'),
                'timestamp': data.get('timestamp'),
                'url': data.get('url')
            }), 200
        return jsonify({'message': 'Job introuvable'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ── Logs d'un build ──────────────────────────────────

@jenkins_bp.route('/logs/<job_name>/<int:build_number>', methods=['GET'])
@keycloak_required
def get_build_logs(job_name, build_number):
    try:
        response = jenkins_get(f"/job/{job_name}/{build_number}/consoleText")
        if response.status_code == 200:
            return jsonify({'job_name': job_name, 'build_number': build_number, 'logs': response.text}), 200
        return jsonify({'message': 'Logs introuvables'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ── Liste des jobs ───────────────────────────────────

@jenkins_bp.route('/jobs', methods=['GET'])
@keycloak_required
def get_jobs():
    try:
        response = jenkins_get("/api/json?tree=jobs[name,color,url]")
        if response.status_code == 200:
            return jsonify(response.json().get('jobs', [])), 200
        return jsonify({'message': 'Erreur Jenkins'}), 500
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ── Historique des builds ────────────────────────────

@jenkins_bp.route('/builds/<job_name>', methods=['GET'])
@keycloak_required
def get_builds(job_name):
    try:
        response = jenkins_get(f"/job/{job_name}/api/json?tree=builds[number,result,duration,timestamp,building]")
        if response.status_code == 200:
            return jsonify(response.json().get('builds', [])), 200
        return jsonify({'message': 'Job introuvable'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ── Arrêter un build ─────────────────────────────────

@jenkins_bp.route('/stop/<job_name>/<int:build_number>', methods=['POST'])
@keycloak_required
def stop_build(job_name, build_number):
    try:
        crumb = get_crumb()
        response = jenkins_post(f"/job/{job_name}/{build_number}/stop", extra_headers=crumb)
        if response.status_code in [200, 201]:
            return jsonify({'message': 'Build arrêté avec succès'}), 200
        return jsonify({'message': "Erreur lors de l'arrêt"}), 500
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ── Créer un job Jenkins ─────────────────────────────

def _build_jenkinsfile(docker_image, k8s_namespace, service_name,
                       replicas, service_port, github_url, github_branch):
    """
    Construit le Jenkinsfile Groovy avec Kaniko via kubectl run.
    Nettoie l'URL Git pour éviter les doublons de préfixe.
    """
    # Sécurisation de l'URL Git : supprime un éventuel préfixe 'git://' redondant
    clean_github_url = github_url
    if clean_github_url.startswith('git://'):
        clean_github_url = clean_github_url[6:]
    if not (clean_github_url.startswith('https://') or clean_github_url.startswith('http://')):
        clean_github_url = 'https://' + clean_github_url

    return "\n".join([
        "pipeline {",
        "    agent any",
        "    environment {",
        "        DOCKER_IMAGE  = '" + docker_image  + "'",
        "        K8S_NAMESPACE = '" + k8s_namespace + "'",
        "        SERVICE_NAME  = '" + service_name  + "'",
        "        REPLICAS      = '" + replicas      + "'",
        "        SERVICE_PORT  = '" + service_port  + "'",
        "        GITHUB_URL    = '" + clean_github_url + "'",
        "        GITHUB_BRANCH = '" + github_branch + "'",
        "        KUBECTL       = '/var/jenkins_home/kubectl'",
        "    }",
        "    stages {",
        "",
        "        stage('Verify Tools') {",
        "            steps {",
        "                sh '$KUBECTL version --client'",
        "                sh '$KUBECTL get nodes'",
        "            }",
        "        }",
        "",
        "        stage('Create Namespace') {",
        "            steps {",
        "                sh '$KUBECTL create namespace $K8S_NAMESPACE --dry-run=client -o yaml | $KUBECTL apply -f -'",
        "            }",
        "        }",
        "",
        "        stage('Build & Push with Kaniko') {",
        "            steps {",
        "                script {",
        "                    sh '$KUBECTL delete pod -n jenkins kaniko-${SERVICE_NAME}-* --ignore-not-found=true --force --grace-period=0 || true'",
        "                    def podYaml = \"\"\"",
        "apiVersion: v1",
        "kind: Pod",
        "metadata:",
        "  name: kaniko-${SERVICE_NAME}-${BUILD_NUMBER}",
        "  namespace: jenkins",
        "  labels:",
        "    app: kaniko-${SERVICE_NAME}",
        "spec:",
        "  serviceAccountName: kaniko-sa",
        "  restartPolicy: Never",
        "  containers:",
        "  - name: kaniko",
        "    image: gcr.io/kaniko-project/executor:latest",
        "    imagePullPolicy: IfNotPresent",
        "    args:",
        "      - --context=git://github.com/wassimmejri/nginx-demo.git",
        "      - --git=branch=main",
        "      - --dockerfile=Dockerfile",
        "      - --destination=${DOCKER_IMAGE}",
        "      - --cache=true",
        "    volumeMounts:",
        "    - name: docker-secret",
        "      mountPath: /kaniko/.docker",
        "  volumes:",
        "  - name: docker-secret",
        "    secret:",
        "      secretName: dockerhub-secret",
        "      items:",
        "      - key: .dockerconfigjson",
        "        path: config.json",
        "\"\"\"",
        "                    writeFile file: 'kaniko-pod.yaml', text: podYaml",
        "                    sh '$KUBECTL apply -f kaniko-pod.yaml'",
        "                }",
        "                sh '''",
        "                    echo \"Attente du build Kaniko...\"",
        "                    for i in $(seq 1 60); do",
        "                        STATUS=$($KUBECTL get pod kaniko-${SERVICE_NAME}-${BUILD_NUMBER} -n jenkins -o jsonpath='{.status.phase}' 2>/dev/null || echo 'Pending')",
        "                        echo \"Status: $STATUS\"",
        "                        if [ \"$STATUS\" = \"Succeeded\" ]; then",
        "                            echo \"Build Kaniko reussi !\"",
        "                            break",
        "                        elif [ \"$STATUS\" = \"Failed\" ]; then",
        "                            echo \"Build Kaniko echoue !\"",
        "                            $KUBECTL logs kaniko-${SERVICE_NAME}-${BUILD_NUMBER} -n jenkins || true",
        "                            exit 1",
        "                        fi",
        "                        sleep 10",
        "                    done",
        "                '''",
        "                sh '$KUBECTL delete pod kaniko-${SERVICE_NAME}-${BUILD_NUMBER} -n jenkins --ignore-not-found=true'",
        "            }",
        "        }",
        "",
        "        stage('Deploy to Kubernetes') {",
        "            steps {",
        "                sh '''",
        "                    $KUBECTL create deployment $SERVICE_NAME \\",
        "                      --image=$DOCKER_IMAGE \\",
        "                      --replicas=$REPLICAS \\",
        "                      -n $K8S_NAMESPACE \\",
        "                      --dry-run=client -o yaml | $KUBECTL apply -f -",
        "                '''",
        "            }",
        "        }",
        "",
        "        stage('Expose Service') {",
        "            steps {",
        "                sh '''",
        "                    $KUBECTL expose deployment $SERVICE_NAME \\",
        "                      --port=$SERVICE_PORT \\",
        "                      --target-port=$SERVICE_PORT \\",
        "                      -n $K8S_NAMESPACE \\",
        "                      --dry-run=client -o yaml | $KUBECTL apply -f -",
        "                '''",
        "            }",
        "        }",
        "",
        "        stage('Verify Deployment') {",
        "            steps {",
        "                sh '$KUBECTL rollout status deployment/$SERVICE_NAME -n $K8S_NAMESPACE --timeout=120s'",
        "                sh '$KUBECTL get pods -n $K8S_NAMESPACE'",
        "                sh '$KUBECTL get svc -n $K8S_NAMESPACE'",
        "            }",
        "        }",
        "",
        "    }",
        "    post {",
        "        success {",
        "            echo 'Deploiement reussi !'",
        "        }",
        "        failure {",
        "            sh '$KUBECTL describe deployment $SERVICE_NAME -n $K8S_NAMESPACE || true'",
        "            echo 'Deploiement echoue !'",
        "        }",
        "    }",
        "}",
    ])


def _create_jenkins_job(job_name, microservice):
    project = microservice.project

    crumb = get_crumb()
    headers = {'Content-Type': 'text/xml'}
    headers.update(crumb)

    jenkinsfile = _build_jenkinsfile(
        docker_image  = microservice.image,
        k8s_namespace = project.k8s_namespace,
        service_name  = microservice.name,
        replicas      = str(microservice.replicas),
        service_port  = str(microservice.port),
        github_url    = project.github_url,
        github_branch = project.github_branch,
    )

    escaped = saxutils.escape(jenkinsfile)

    config_xml = (
        "<?xml version='1.1' encoding='UTF-8'?>"
        '<flow-definition plugin="workflow-job">'
        "<actions/>"
        "<description></description>"
        "<keepDependencies>false</keepDependencies>"
        "<properties/>"
        '<definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition"'
        ' plugin="workflow-cps">'
        "<script>" + escaped + "</script>"
        "<sandbox>true</sandbox>"
        "</definition>"
        "<triggers/>"
        "<disabled>false</disabled>"
        "</flow-definition>"
    )

    print(f"[DEBUG] config_xml length: {len(config_xml)}")

    response = jenkins_post(
        f"/createItem?name={job_name}",
        data=config_xml.encode('utf-8'),
        extra_headers=headers
    )
    print(f"Create job: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    return response.status_code in [200, 201]