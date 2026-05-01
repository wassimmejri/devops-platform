import eventlet
from flask import request
from flask_socketio import Namespace
from app.services.metrics_service import get_metric, get_history_metrics

QUERIES = {
    'cpu': '(1 - avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[2m]))) * 100',
    'ram': '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100',
}

class MetricsNamespace(Namespace):

    def __init__(self, namespace, sio):
        super().__init__(namespace)
        self.socketio = sio

    def on_connect(self):
        print(f'[WS /metrics] Client connecté : {request.sid}')

    def on_disconnect(self):
        print(f'[WS /metrics] Client déconnecté : {request.sid}')

    def on_watch_metrics(self, data):
        sid      = request.sid
        interval = int(data.get('interval', 5))
        print(f'[WS /metrics] watch_metrics → interval={interval}s, sid={sid}')

        def stream():
            count = 0
            while True:
                try:
                    # Métriques instantanées (votre code existant)
                    payload = {
                        key: get_metric(query)
                        for key, query in QUERIES.items()
                    }
                    self.socketio.emit('metrics_update', payload,
                                       namespace='/metrics', room=sid)

                    # 🔥 NOUVEAU : historique toutes les 3 itérations
                    count += 1
                    if count % 3 == 0:
                        history = get_history_metrics(minutes=5, step=15)
                        self.socketio.emit('history_update', history,
                                           namespace='/metrics', room=sid)

                except Exception as e:
                    print(f'[WS /metrics] Erreur: {e}')
                    self.socketio.emit('error', {'msg': str(e)},
                                       namespace='/metrics', room=sid)
                eventlet.sleep(interval)

        eventlet.spawn(stream)