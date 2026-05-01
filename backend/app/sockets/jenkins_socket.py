import eventlet
from flask import request, current_app
from flask_socketio import Namespace
from app.routes.jenkins import jenkins_get


class JenkinsLogsNamespace(Namespace):

    def __init__(self, namespace, sio):
        super().__init__(namespace)
        self.socketio = sio

    def on_connect(self):
        print(f'[WS /jenkins-logs] Client connecté : {request.sid}')

    def on_disconnect(self):
        print(f'[WS /jenkins-logs] Client déconnecté : {request.sid}')

    def on_stream_build_logs(self, data):
        sid          = request.sid
        job_name     = data.get('job_name')
        build_number = data.get('build_number')

        print(f'[WS /jenkins-logs] stream_build_logs → job={job_name}, build={build_number}, sid={sid}')

        if not job_name or not build_number:
            self.socketio.emit(
                'log_error',
                {'message': 'job_name et build_number requis'},
                namespace='/jenkins-logs',
                room=sid
            )
            return

        # ✅ Capture le contexte Flask AVANT de spawner le thread
        app = current_app._get_current_object()

        def stream():
            # ✅ Utilise le contexte Flask dans le thread
            with app.app_context():
                sent_lines  = 0
                max_retries = 100  # ~5 minutes (100 × 3s)

                for _ in range(max_retries):
                    try:
                        # ── Logs console ──────────────────────────────────────
                        response = jenkins_get(
                            f"/job/{job_name}/{build_number}/consoleText"
                        )
                        print(f'[WS /jenkins-logs] consoleText status={response.status_code}')

                        if response.status_code == 200:
                            all_lines = response.text.split('\n')
                            new_lines = all_lines[sent_lines:]

                            for line in new_lines:
                                if line.strip():
                                    self.socketio.emit(
                                        'build_log_line',
                                        {
                                            'line':         line,
                                            'job_name':     job_name,
                                            'build_number': build_number,
                                        },
                                        namespace='/jenkins-logs',
                                        room=sid
                                    )
                                    eventlet.sleep(0)

                            sent_lines = len(all_lines)

                        elif response.status_code == 404:
                            print(f'[WS /jenkins-logs] Build pas encore prêt, attente...')
                            eventlet.sleep(3)
                            continue

                        # ── Statut du build ───────────────────────────────────
                        status_resp = jenkins_get(
                            f"/job/{job_name}/{build_number}/api/json"
                        )
                        print(f'[WS /jenkins-logs] build status={status_resp.status_code}')

                        if status_resp.status_code == 200:
                            build_data  = status_resp.json()
                            is_building = build_data.get('building', True)

                            if not is_building:
                                result = build_data.get('result', 'UNKNOWN')
                                self.socketio.emit(
                                    'build_finished',
                                    {
                                        'job_name':     job_name,
                                        'build_number': build_number,
                                        'result':       result,
                                    },
                                    namespace='/jenkins-logs',
                                    room=sid
                                )
                                print(f'[WS /jenkins-logs] Build terminé : {result}')
                                break

                    except Exception as e:
                        print(f'[WS /jenkins-logs] Erreur: {e}')
                        self.socketio.emit(
                            'log_error',
                            {'message': str(e)},
                            namespace='/jenkins-logs',
                            room=sid
                        )
                        break

                    eventlet.sleep(3)

        eventlet.spawn(stream)