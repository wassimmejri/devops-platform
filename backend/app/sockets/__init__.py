def register_sockets(socketio):
    from .pods_socket import PodStatusNamespace
    from .metrics_socket import MetricsNamespace
    from .logs_socket import LogsNamespace
    from .alerts_socket import AlertsNamespace 

    socketio.on_namespace(PodStatusNamespace('/pods', socketio))      # ← ajouter socketio
    socketio.on_namespace(MetricsNamespace('/metrics', socketio))     # ← ajouter socketio
    socketio.on_namespace(LogsNamespace('/logs', socketio))
    socketio.on_namespace(AlertsNamespace('/alerts', socketio))