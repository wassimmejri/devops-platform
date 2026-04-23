import eventlet
from flask import request
from flask_socketio import Namespace
from app.services.k8s_service import get_k8s_clients
from kubernetes import watch

class PodStatusNamespace(Namespace):

    def __init__(self, namespace, sio):
        super().__init__(namespace)
        self.socketio = sio

    def on_connect(self):
        print(f'[WS /pods] Client connecté : {request.sid}')

    def on_disconnect(self):
        print(f'[WS /pods] Client déconnecté : {request.sid}')

    def on_watch_pods(self, data):
        sid       = request.sid
        namespace = data.get('namespace', '')
        print(f'[WS /pods] watch_pods → ns={namespace or "ALL"}, sid={sid}')

        def stream():
            try:
                _, core_v1 = get_k8s_clients()
                w = watch.Watch()

                # Si namespace vide → watch tous les namespaces
                list_fn = (core_v1.list_pod_for_all_namespaces
                           if not namespace
                           else core_v1.list_namespaced_pod)
                kwargs = {} if not namespace else {'namespace': namespace}

                for event in w.stream(list_fn, timeout_seconds=0, **kwargs):
                    pod = event['object']
                    self.socketio.emit('pod_status', {
                        'event':     event['type'],
                        'name':      pod.metadata.name,
                        'namespace': pod.metadata.namespace,
                        'status':    pod.status.phase,
                        'ready':     self._is_ready(pod),
                        'restarts':  self._get_restarts(pod),
                        'node':      pod.spec.node_name,
                    }, namespace='/pods', room=sid)
                    eventlet.sleep(0)

            except Exception as e:
                print(f'[WS /pods] Erreur: {e}')
                self.socketio.emit('error', {'msg': str(e)},
                                   namespace='/pods', room=sid)

        eventlet.spawn(stream)

    def _is_ready(self, pod):
        if not pod.status.conditions:
            return False
        return any(
            c.type == 'Ready' and c.status == 'True'
            for c in pod.status.conditions
        )

    def _get_restarts(self, pod):
        if not pod.status.container_statuses:
            return 0
        return sum(c.restart_count for c in pod.status.container_statuses)