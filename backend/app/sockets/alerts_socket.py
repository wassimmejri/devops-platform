import eventlet
from flask import request
from flask_socketio import Namespace
from app.services.alertmanager_service import get_alerts

class AlertsNamespace(Namespace):

    def __init__(self, namespace, sio):
        super().__init__(namespace)
        self.socketio = sio

    def on_connect(self):
        print(f'[WS /alerts] Client connecté : {request.sid}')

    def on_disconnect(self):
        print(f'[WS /alerts] Client déconnecté : {request.sid}')

    def on_watch_alerts(self, data):
        sid      = request.sid
        interval = int(data.get('interval', 15))
        print(f'[WS /alerts] watch_alerts → interval={interval}s, sid={sid}')

        def stream():
            while True:
                try:
                    alerts = get_alerts()
                    # Compter par sévérité
                    summary = {
                        'critical': 0,
                        'warning':  0,
                        'info':     0,
                        'total':    len(alerts)
                    }
                    for alert in alerts:
                        severity = alert.get('labels', {}).get('severity', 'info').lower()
                        if severity in summary:
                            summary[severity] += 1

                    self.socketio.emit('alerts_update', {
                        'alerts':  alerts,
                        'summary': summary,
                    }, namespace='/alerts', room=sid)
                    print(f'[WS /alerts] {len(alerts)} alertes envoyées → {sid}')
                except Exception as e:
                    print(f'[WS /alerts] Erreur: {e}')
                    self.socketio.emit('error', {'msg': str(e)},
                                       namespace='/alerts', room=sid)
                eventlet.sleep(interval)

        eventlet.spawn(stream)