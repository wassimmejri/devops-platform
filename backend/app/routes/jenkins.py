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

    # Ne force le Content-Type que si extra_headers ne l'a pas déjà défini
    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    url = f"{get_jenkins_url()}{path}"
    print(f"[DEBUG] Jenkins POST {url} headers={headers} data={data}")

    try:
        return requests.post(
            url,
            auth=get_auth(),
            headers=headers,
            data=data,
            timeout=10
        )
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

        # Vérifier si job existe
        check = jenkins_get(f"/job/{job_name}/api/json")
        print(f"[DEBUG] Check job status code: {check.status_code}")

        if check.status_code == 404:
            print("[DEBUG] Job introuvable, création en cours...")
            result = _create_jenkins_job(job_name, microservice)
            print(f"[DEBUG] Job creation result: {result}")

            if not result:
                return jsonify({'message': 'Erreur lors de la création du job Jenkins'}), 500

        # Récupérer crumb
        crumb = get_crumb()
        print(f"[DEBUG] Crumb: {crumb}")

        if not crumb:
            return jsonify({'message': "Impossible d'obtenir le crumb Jenkins"}), 500

        # Version envoyée
        data = request.get_json() or {}
        version = data.get('version', 'latest')

        # Strip du tag pour éviter double tag (ex: wassimdev/nginx-demo:latest:latest)
        image_base = microservice.image.split(':')[0]

        params = {
            "DOCKER_IMAGE": f"{image_base}:{version}",
            "K8S_NAMESPACE": microservice.project.k8s_namespace,
            "SERVICE_NAME": microservice.name,
            "REPLICAS": str(microservice.replicas),
            "SERVICE_PORT": str(microservice.port)
        }

        print(f"[DEBUG] Params: {params}")
        print(f"[DEBUG] DOCKER_IMAGE resolved: {image_base}:{version}")

        # Déclencher pipeline Jenkins
        trigger = jenkins_post(
            f"/job/{job_name}/buildWithParameters",
            data=params,
            extra_headers=crumb
        )

        print(f"[DEBUG] Trigger status code: {trigger.status_code}")
        print(f"[DEBUG] Response: {trigger.text}")

        if trigger.status_code not in [200, 201, 202, 302]:
            return jsonify({
                'message': f'Erreur déclenchement pipeline (status {trigger.status_code})',
                'detail': trigger.text
            }), 500

        # Sauvegarde du déploiement en DB (sans le build number pour l'instant)
        deployment = Deployment(
            version=version,
            status='building',
            microservice_id=microservice_id,
            triggered_by=user.id,
            created_at=datetime.utcnow()
        )

        microservice.status = 'deploying'

        db.session.add(deployment)
        db.session.commit()

        # ✅ Récupère le numéro du build qui vient d'être déclenché
        build_info = jenkins_get(f"/job/{job_name}/lastBuild/api/json")
        if build_info.status_code == 200:
            build_number = build_info.json().get('number')
            deployment.jenkins_build_number = build_number
            db.session.commit()
            print(f"[DEBUG] Build number {build_number} enregistré pour le déploiement")
        else:
            print("[WARNING] Impossible de récupérer le numéro de build")

        print("[DEBUG] Deployment saved in DB")

        return jsonify({
            'message': 'Déploiement déclenché avec succès',
            'deployment': deployment.to_dict()
        }), 201

    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR] Exception: {str(e)}")

        return jsonify({
            'message': 'Erreur interne du serveur',
            'detail': str(e)
        }), 500

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


# ── Logs d'un build (numéro précis) ──────────────────

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


# ── Logs du dernier build ─────────────────────────────

@jenkins_bp.route('/logs/<job_name>/lastBuild', methods=['GET'])
@keycloak_required
def get_last_build_logs(job_name):
    try:
        info = jenkins_get(f"/job/{job_name}/lastBuild/api/json")
        if info.status_code != 200:
            return jsonify({'logs': 'Aucun build trouvé pour ce job.'}), 200

        build_number = info.json().get('number')
        result       = info.json().get('result')
        building     = info.json().get('building')

        logs_resp = jenkins_get(f"/job/{job_name}/{build_number}/consoleText")
        logs_text = logs_resp.text if logs_resp.status_code == 200 else 'Logs introuvables.'

        return jsonify({
            'job_name':     job_name,
            'build_number': build_number,
            'result':       result,
            'building':     building,
            'logs':         logs_text
        }), 200

    except Exception as e:
        return jsonify({'logs': f'Erreur: {str(e)}'}), 200


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
        "        KUBECTL       = '$HOME/kubectl'",         # ← home directory
        "    }",
        "    stages {",
        "",
        "        stage('Install kubectl') {",
        "            steps {",
        "                sh '''",
        "                    if ! command -v $HOME/kubectl > /dev/null 2>&1; then",
        "                        curl -LO https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl",
        "                        chmod +x kubectl",
        "                        mv kubectl $HOME/kubectl",  # ← pas besoin de root
        "                    fi",
        "                    $HOME/kubectl version --client",
        "                '''",
        "            }",
        "        }",
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
        "      - --context=git://" + clean_github_url.replace('https://', '') + "",
        "      - --git=branch=" + github_branch,
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
        "            sh '''curl -s -X POST http://172.25.50.101:5000/api/jenkins/webhook \\",
        "              -H \"Content-Type: application/json\" \\",
        "              -d \"{\\\"job_name\\\": \\\"$JOB_NAME\\\", \\\"build_number\\\": $BUILD_NUMBER, \\\"result\\\": \\\"SUCCESS\\\"}\"'''",
        "            echo 'Deploiement reussi !'",
        "        }",
        "        failure {",
        "            sh '''curl -s -X POST http://172.25.50.101:5000/api/jenkins/webhook \\",
        "              -H \"Content-Type: application/json\" \\",
        "              -d \"{\\\"job_name\\\": \\\"$JOB_NAME\\\", \\\"build_number\\\": $BUILD_NUMBER, \\\"result\\\": \\\"FAILURE\\\"}\"'''",
        "            sh '$KUBECTL describe deployment $SERVICE_NAME -n $K8S_NAMESPACE || true'",
        "            echo 'Deploiement echoue !'",
        "        }",
        "    }",
        "}",
    ])


def _create_jenkins_job(job_name, microservice):
    project = microservice.project
    crumb   = get_crumb()
    headers = {'Content-Type': 'text/xml'}
    headers.update(crumb)

    # Variables passées au pipeline comme paramètres Jenkins
    config_xml = (
        "<?xml version='1.1' encoding='UTF-8'?>"
        '<flow-definition plugin="workflow-job">'
        "<actions/>"
        "<description></description>"
        "<keepDependencies>false</keepDependencies>"
        "<properties>"
        '<hudson.model.ParametersDefinitionProperty>'
        '<parameterDefinitions>'
        # DOCKER_IMAGE
        '<hudson.model.StringParameterDefinition>'
        '<name>DOCKER_IMAGE</name>'
        f'<defaultValue>{microservice.image}</defaultValue>'
        '</hudson.model.StringParameterDefinition>'
        # K8S_NAMESPACE
        '<hudson.model.StringParameterDefinition>'
        '<name>K8S_NAMESPACE</name>'
        f'<defaultValue>{project.k8s_namespace}</defaultValue>'
        '</hudson.model.StringParameterDefinition>'
        # SERVICE_NAME
        '<hudson.model.StringParameterDefinition>'
        '<name>SERVICE_NAME</name>'
        f'<defaultValue>{microservice.name}</defaultValue>'
        '</hudson.model.StringParameterDefinition>'
        # REPLICAS
        '<hudson.model.StringParameterDefinition>'
        '<name>REPLICAS</name>'
        f'<defaultValue>{microservice.replicas}</defaultValue>'
        '</hudson.model.StringParameterDefinition>'
        # SERVICE_PORT
        '<hudson.model.StringParameterDefinition>'
        '<name>SERVICE_PORT</name>'
        f'<defaultValue>{microservice.port}</defaultValue>'
        '</hudson.model.StringParameterDefinition>'
        '</parameterDefinitions>'
        '</hudson.model.ParametersDefinitionProperty>'
        '</properties>'
        # SCM → lit le Jenkinsfile du repo GitHub
        '<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition"'
        ' plugin="workflow-cps">'
        '<scm class="hudson.plugins.git.GitSCM" plugin="git">'
        '<configVersion>2</configVersion>'
        '<userRemoteConfigs>'
        '<hudson.plugins.git.UserRemoteConfig>'
        f'<url>{project.github_url}</url>'
        '</hudson.plugins.git.UserRemoteConfig>'
        '</userRemoteConfigs>'
        '<branches>'
        '<hudson.plugins.git.BranchSpec>'
        f'<name>*/{project.github_branch}</name>'
        '</hudson.plugins.git.BranchSpec>'
        '</branches>'
        '</scm>'
        '<scriptPath>Jenkinsfile</scriptPath>'    # ← lit Jenkinsfile du repo
        '<lightweight>true</lightweight>'
        '</definition>'
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


# ── Webhook Jenkins ──────────────────────────────────

@jenkins_bp.route('/webhook', methods=['POST'])
def jenkins_webhook():
    data         = request.get_json() or {}
    job_name     = data.get('job_name')
    build_number = data.get('build_number')
    result       = data.get('result')

    print(f"[Webhook] job={job_name}, build={build_number}, result={result}")

    if not job_name or not result:
        return jsonify({'message': 'Données manquantes'}), 400

    microservice = Microservice.query.filter_by(jenkins_job_name=job_name).first()
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404

    # ✅ Cherche le dernier deployment en building
    deployment = Deployment.query.filter_by(
        microservice_id=microservice.id,
        status='building'
    ).order_by(Deployment.created_at.desc()).first()

    if result == 'SUCCESS':
        microservice.status = 'running'
        if deployment:
            deployment.status      = 'success'
            deployment.finished_at = datetime.utcnow()
            print(f"[Webhook] Deployment {deployment.id} → success")
        else:
            print(f"[Webhook] Aucun deployment en building trouvé")
    else:
        microservice.status = 'error'
        if deployment:
            deployment.status      = 'failed'
            deployment.finished_at = datetime.utcnow()
            print(f"[Webhook] Deployment {deployment.id} → failed")

    db.session.commit()
    return jsonify({'message': 'Statut mis à jour'}), 200

@jenkins_bp.route('/deployments/recent', methods=['GET'])
@keycloak_required
def get_recent_deployments():
    user = get_or_create_user(request.userinfo)
    
    deployments = (
        Deployment.query
        .join(Microservice)
        .join(Project)
        .filter(Project.owner_id == user.id)
        .order_by(Deployment.created_at.desc())
        .limit(10)
        .all()
    )
    
    return jsonify([{
        'id':           d.id,
        'name':         d.microservice.name,
        'namespace':    d.microservice.project.k8s_namespace,
        'version':      d.version,
        'status':       d.status,
        'created_at':   d.created_at.isoformat() if d.created_at else None,
        'finished_at':  d.finished_at.isoformat() if d.finished_at else None,
    } for d in deployments])


# ── Sync / Polling fallback ──────────────────────────

@jenkins_bp.route('/sync/<int:microservice_id>', methods=['POST'])
@keycloak_required
def sync_status(microservice_id):
    user = get_or_create_user(request.userinfo)
    microservice = Microservice.query.join(Project).filter(
        Microservice.id == microservice_id,
        Project.owner_id == user.id
    ).first()
    if not microservice:
        return jsonify({'message': 'Microservice introuvable'}), 404

    try:
        job_name  = microservice.jenkins_job_name
        response  = jenkins_get(f"/job/{job_name}/lastBuild/api/json")
        if response.status_code != 200:
            return jsonify({'message': 'Build introuvable'}), 404

        build_data   = response.json()
        result       = build_data.get('result')
        building     = build_data.get('building')
        build_number = build_data.get('number')
        duration     = build_data.get('duration', 0) // 1000

        deployment = Deployment.query.filter_by(
            microservice_id=microservice_id,
            jenkins_build_number=build_number
        ).first()

        if building:
            microservice.status = 'deploying'
            if deployment:
                deployment.status = 'building'
        elif result == 'SUCCESS':
            microservice.status = 'running'
            if deployment:
                deployment.status      = 'success'
                deployment.duration    = duration
                deployment.finished_at = datetime.utcnow()
        elif result in ('FAILURE', 'ABORTED', 'UNSTABLE'):
            microservice.status = 'error'
            if deployment:
                deployment.status      = 'failed'
                deployment.duration    = duration
                deployment.finished_at = datetime.utcnow()

        db.session.commit()
        return jsonify({
            'microservice_status': microservice.status,
            'build_number':        build_number,
            'result':              result,
            'building':            building,
        }), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500