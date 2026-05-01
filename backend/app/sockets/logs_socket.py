import eventlet
import json
from datetime import datetime, timezone, timedelta
from flask import request
from flask_socketio import Namespace

class LogsNamespace(Namespace):

    def __init__(self, namespace, sio):
        super().__init__(namespace)
        self.socketio = sio

    def on_connect(self):
        print(f'[WS /logs] Client connecté : {request.sid}')

    def on_disconnect(self):
        print(f'[WS /logs] Client déconnecté : {request.sid}')

    def on_stream_logs(self, data):
        sid       = request.sid
        namespace = data.get('namespace', 'default')
        pod       = data.get('pod')
        interval  = int(data.get('interval', 3))

        print(f'[WS /logs] stream_logs → ns={namespace}, pod={pod}, sid={sid}')

        if not pod:
            self.socketio.emit('error', {'msg': 'pod requis'},
                               namespace='/logs', room=sid)
            return

        def stream():
            from app.services.logs_service import get_logs
            seen = set()
            while True:
                try:
                    result  = get_logs(pod, namespace, limit=200)
                    streams = result.get('data', {}).get('result', [])

                    # ── DEBUG ──────────────────────────────────────────────
                    print(f'[DEBUG socket] streams count={len(streams)}')
                    if streams:
                        first_values = streams[0].get('values', [])
                        print(f'[DEBUG socket] first stream values count={len(first_values)}')
                        if first_values:
                            print(f'[DEBUG socket] sample value={first_values[0]}')
                    else:
                        print(f'[DEBUG socket] result complet={result}')
                    # ───────────────────────────────────────────────────────

                    new_lines = []
                    for stream_entry in streams:
                        for ts, raw_line in stream_entry.get('values', []):
                            if ts in seen:
                                continue
                            seen.add(ts)
                            new_lines.append({
                                'ts':   ts,
                                'line': self._parse_line(raw_line),
                            })

                    print(f'[DEBUG socket] new_lines={len(new_lines)}, seen total={len(seen)}')

                    if new_lines:
                        new_lines.sort(key=lambda x: x['ts'])
                        self.socketio.emit(
                            'log_line',
                            {'pod': pod, 'lines': new_lines},
                            namespace='/logs',
                            room=sid,
                        )
                        print(f'[WS /logs] {len(new_lines)} lignes envoyées → {sid}')
                    else:
                        print(f'[DEBUG socket] aucune nouvelle ligne (tout déjà dans seen)')

                except Exception as e:
                    print(f'[WS /logs] Erreur stream: {e}')
                    self.socketio.emit('error', {'msg': str(e)},
                                       namespace='/logs', room=sid)

                eventlet.sleep(interval)

        eventlet.spawn(stream)

    def _parse_line(self, raw_line: str) -> str:
        try:
            obj = json.loads(raw_line)
            time = obj.get('time', '')
            if time:
                utc_time   = datetime.fromisoformat(time.replace('Z', '+00:00'))
                local_time = utc_time.astimezone(timezone(timedelta(hours=2)))
                time       = local_time.strftime('%Y-%m-%d %H:%M:%S')
            level = obj.get('level', '').upper()
            msg   = obj.get('msg', raw_line)
            return f"[{time}] {level} — {msg}"
        except (json.JSONDecodeError, TypeError, ValueError):
            return raw_line