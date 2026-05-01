import time
from datetime import datetime
import requests
from os import getenv

def sync_jenkins_deployments(app):
    time.sleep(5)
    with app.app_context():
        from app import db, socketio
        from app.models.deployment import Deployment

        print("[SYNC] Service de synchronisation actif", flush=True)

        while True:
            try:
                deployments = Deployment.query.filter_by(status='building').all()
                print(f"[SYNC] {len(deployments)} déploiement(s) en building", flush=True)

                for dep in deployments:
                    if not dep.microservice:
                        continue
                    job_name = dep.microservice.jenkins_job_name

                    url = f"{app.config['JENKINS_URL']}/job/{job_name}/lastBuild/api/json"
                    print(f"[SYNC]   → appel lastBuild: {url}", flush=True)

                    # ← AJOUT : header Host pour le routage Ingress
                    jenkins_host = app.config.get('JENKINS_HOST') or getenv('JENKINS_HOST')
                    headers = {'Host': jenkins_host} if jenkins_host else {}

                    try:
                        resp = requests.get(
                            url,
                            auth=(app.config['JENKINS_USER'], app.config['JENKINS_TOKEN']),
                            headers=headers,   # ← AJOUT
                            timeout=5
                        )
                        print(f"[SYNC]   → statut HTTP {resp.status_code}", flush=True)
                        if resp.status_code != 200:
                            print(f"[SYNC]   → réponse non 200: {resp.text[:200]}", flush=True)
                            continue

                        data = resp.json()
                        building = data.get('building', False)
                        result   = data.get('result')
                        print(f"[SYNC]   → building={building}, result={result}", flush=True)

                        if not building and result is not None:
                            dep.status          = 'success' if result == 'SUCCESS' else 'failed'
                            dep.finished_at     = datetime.utcnow()
                            dep.microservice.status = 'running' if result == 'SUCCESS' else 'error'
                            db.session.commit()
                            print(f"[SYNC]   → déploiement {dep.id} mis à jour: {dep.status}", flush=True)

                            socketio.emit('deployment_update', {
                                'id':          dep.id,
                                'name':        dep.microservice.name,
                                'namespace':   dep.microservice.project.k8s_namespace,
                                'version':     dep.version,
                                'status':      dep.status,
                                'created_at':  dep.created_at.isoformat() if dep.created_at else None,
                                'finished_at': dep.finished_at.isoformat() if dep.finished_at else None
                            }, namespace='/deployments', to=None)

                    except Exception as e:
                        print(f"[SYNC]   → erreur appel Jenkins: {e}", flush=True)

            except Exception as e:
                print(f"[SYNC] ERREUR BOUCLE: {e}", flush=True)

            time.sleep(30)