import { Injectable, OnDestroy } from '@angular/core';
import { Observable } from 'rxjs';
import { io, Socket } from 'socket.io-client';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class SocketService implements OnDestroy {

  private sockets = new Map<string, Socket>();

  constructor(private auth: AuthService) {}

  // ── PODS ──────────────────────────────────────────────────────────────────

  watchPods(namespace: string): Observable<any> {
    const socket = this.connect('/pods');
    socket.emit('watch_pods', { namespace });
    return this.listen(socket, 'pod_status');
  }

  // ── METRICS ───────────────────────────────────────────────────────────────

  watchMetrics(interval = 5): Observable<any> {
    const socket = this.connect('/metrics');
    socket.emit('watch_metrics', { interval });
    return this.listen(socket, 'metrics_update');
  }

  // ── LOGS ──────────────────────────────────────────────────────────────────

  streamLogs(namespace: string, pod: string, interval = 3): Observable<any> {
    this.disconnect('/logs');
    const socket = this.connect('/logs');
    return new Observable(observer => {
      const onConnect = () => {
        console.log('[WS /logs] Connecté, envoi stream_logs');
        socket.emit('stream_logs', { namespace, pod, interval });
      };
      const onLogLine = (data: any) => observer.next(data);
      const onError   = (err: any)  => observer.error(err);

      if (socket.connected) {
        socket.emit('stream_logs', { namespace, pod, interval });
      } else {
        socket.once('connect', onConnect);
      }

      socket.on('log_line', onLogLine);
      socket.on('error',    onError);

      return () => {
        socket.off('connect',  onConnect);
        socket.off('log_line', onLogLine);
        socket.off('error',    onError);
      };
    });
  }

  // ── ALERTS ────────────────────────────────────────────────────────────────

  watchAlerts(interval = 15): Observable<any> {
    const socket = this.connect('/alerts');
    socket.emit('watch_alerts', { interval });
    return this.listen(socket, 'alerts_update');
  }

  // ── DEPLOYMENTS ───────────────────────────────────────────────────────────

  watchDeployments(): Observable<any> {
    const socket = this.connect('/deployments');
    // Écouter l'événement deployment_update émis par le backend
    return this.listen(socket, 'deployment_update');
  }

  // ── DISCONNECT ────────────────────────────────────────────────────────────

  disconnect(namespace: string): void {
    const socket = this.sockets.get(namespace);
    if (socket) {
      socket.disconnect();
      socket.removeAllListeners();
      this.sockets.delete(namespace);
      console.log(`[WS] Déconnecté de ${namespace}`);
    }
  }

  ngOnDestroy(): void {
    this.sockets.forEach((socket) => {
      socket.disconnect();
      socket.removeAllListeners();
    });
    this.sockets.clear();
  }

  // ── PRIVÉ ─────────────────────────────────────────────────────────────────

  private connect(namespace: string): Socket {
    if (this.sockets.has(namespace)) {
      const existing = this.sockets.get(namespace)!;
      if (!existing.connected) {
        existing.connect();
      }
      return existing;
    }

    const socket = io(`${environment.wsUrl}${namespace}`, {
      transports:        ['websocket'],
      auth:              { token: this.auth.getToken() },
      autoConnect:       true,
      reconnection:      true,
      reconnectionDelay: 1000,
    });

    socket.on('connect',    () => console.log(`[WS] Connecté à ${namespace}`));
    socket.on('disconnect', () => console.log(`[WS] Déconnecté de ${namespace}`));
    socket.on('error',      (err: any) => console.error(`[WS] Erreur ${namespace}:`, err));

    this.sockets.set(namespace, socket);
    return socket;
  }

  streamJenkinsBuildLogs(jobName: string, buildNumber: number): Observable<any> {
  this.disconnect('/jenkins-logs');
  const socket = this.connect('/jenkins-logs');

  return new Observable(observer => {
    const onConnect = () => {
      console.log('[WS /jenkins-logs] Connecté, envoi stream_build_logs');
      socket.emit('stream_build_logs', {
        job_name:     jobName,
        build_number: buildNumber
      });
    };

    const onLogLine  = (data: any) => observer.next({ type: 'line',     ...data });
    const onFinished = (data: any) => observer.next({ type: 'finished', ...data });
    const onError    = (err: any)  => observer.error(err);

    if (socket.connected) {
      socket.emit('stream_build_logs', {
        job_name:     jobName,
        build_number: buildNumber
      });
    } else {
      socket.once('connect', onConnect);
    }

    socket.on('build_log_line', onLogLine);
    socket.on('build_finished', onFinished);
    socket.on('log_error',      onError);

    return () => {
      socket.off('connect',      onConnect);
      socket.off('build_log_line', onLogLine);
      socket.off('build_finished', onFinished);
      socket.off('log_error',      onError);
    };
  });
}

watchHistory(): Observable<any> {
  const socket = this.connect('/metrics');
  return this.listen(socket, 'history_update');
}

  private listen(socket: Socket, event: string): Observable<any> {
    return new Observable(observer => {
      socket.on(event,   (data: any) => observer.next(data));
      socket.on('error', (err: any)  => observer.error(err));
      return () => {
        socket.off(event);
        socket.off('error');
      };
    });
  }
}