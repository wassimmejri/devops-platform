import { Injectable, OnDestroy } from '@angular/core';
import { Observable } from 'rxjs';
import { io, Socket } from 'socket.io-client';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class SocketService implements OnDestroy {

  // Map namespace → socket instance
  private sockets = new Map<string, Socket>();

  constructor(private auth: AuthService) {}

  // ── PODS ──────────────────────────────────────────────────────────────────

  /**
   * Watch les pods d'un namespace.
   * Émet : pod_status { event, name, status, ready, restarts, node }
   */
  watchPods(namespace: string): Observable<any> {
    const socket = this.connect('/pods');
    socket.emit('watch_pods', { namespace });
    return this.listen(socket, 'pod_status');
  }

  // ── METRICS ───────────────────────────────────────────────────────────────

  /**
   * Poll les métriques CPU/RAM des nœuds toutes les `interval` secondes.
   * Émet : metrics_update { cpu: [...], ram: [...] }
   */
  watchMetrics(interval = 5): Observable<any> {
    const socket = this.connect('/metrics');
    socket.emit('watch_metrics', { interval });
    return this.listen(socket, 'metrics_update');
  }

  // ── LOGS ──────────────────────────────────────────────────────────────────

  /**
   * Stream les logs d'un pod Loki toutes les `interval` secondes.
   * Émet : log_line { pod, lines: [{ ts, line }] }
   */
  streamLogs(namespace: string, pod: string, interval = 3): Observable<any> {
    const socket = this.connect('/logs');
    socket.emit('stream_logs', { namespace, pod, interval });
    return this.listen(socket, 'log_line');
  }
    // ── ALERTS ────────────────────────────────────────────────────────────────
  watchAlerts(interval = 15): Observable<any> {
    const socket = this.connect('/alerts');
    socket.emit('watch_alerts', { interval });
    return this.listen(socket, 'alerts_update');
  }

  // ── DISCONNECT ────────────────────────────────────────────────────────────

  /** Déconnecte un namespace précis (appelle dans ngOnDestroy des composants) */
  disconnect(namespace: string): void {
    const socket = this.sockets.get(namespace);
    if (socket) {
      socket.disconnect();
      this.sockets.delete(namespace);
      console.log(`[WS] Déconnecté de ${namespace}`);
    }
  }

  /** Déconnecte tout (appelé automatiquement si le service est détruit) */
  ngOnDestroy(): void {
    this.sockets.forEach((socket, ns) => {
      socket.disconnect();
      console.log(`[WS] Déconnecté de ${ns}`);
    });
    this.sockets.clear();
  }

  // ── PRIVÉ ─────────────────────────────────────────────────────────────────

  /**
   * Crée ou réutilise une socket pour un namespace.
   * Utilise getToken() de ton AuthService existant.
   */
  private connect(namespace: string): Socket {
    if (this.sockets.has(namespace)) {
      return this.sockets.get(namespace)!;
    }

    const socket = io(`${environment.wsUrl}${namespace}`, {
      transports: ['websocket'],
      auth: { token: this.auth.getToken() },  // ← getToken() de ton AuthService
      autoConnect: true,
    });

    socket.on('connect', () =>
      console.log(`[WS] Connecté à ${namespace}`)
    );
    socket.on('disconnect', () =>
      console.log(`[WS] Déconnecté de ${namespace}`)
    );
    socket.on('error', (err: any) =>
      console.error(`[WS] Erreur ${namespace}:`, err)
    );

    this.sockets.set(namespace, socket);
    return socket;
  }

  /** Wrappe un événement socket en Observable propre */
  private listen(socket: Socket, event: string): Observable<any> {
    return new Observable(observer => {
      socket.on(event, (data: any) => observer.next(data));
      socket.on('error', (err: any) => observer.error(err));

      // Cleanup : retire les listeners quand on unsubscribe
      return () => {
        socket.off(event);
        socket.off('error');
      };
    });
  }
}