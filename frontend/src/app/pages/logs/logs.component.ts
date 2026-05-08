import { Component, OnInit, OnDestroy } from '@angular/core';
import { ProjectService } from '../../services/project.service';
import { K8sService } from '../../services/k8s.service';
import { LogsService } from '../../services/logs.service';
import { SocketService } from '../../services/socket.service';
import { MessageService } from 'primeng/api';
import { Subscription } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-logs',
  templateUrl: './logs.component.html',
  styleUrls: ['./logs.component.scss']
})
export class LogsComponent implements OnInit, OnDestroy {

  namespaces: string[] = [];
  selectedNamespace: string = '';

  pods: any[] = [];
  podOptions: any[] = [];
  selectedPod: string = '';

  logs: any[] = [];
  loadingNamespaces = false;
  loadingPods = false;
  loadingLogs = false;

  wsActive = false;
  private logsSub?: Subscription;
  isAdmin = false;

  autoRefresh = true;
  refreshInterval = 10;
  private autoRefreshTimer: any = null;

  constructor(
    private projectService: ProjectService,
    private k8sService: K8sService,
    private logsService: LogsService,
    private socketService: SocketService,
    private messageService: MessageService,
    private authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.isAdmin = this.authService.isAdmin();
    this.loadNamespaces();
  }

  ngOnDestroy(): void {
    this.stopStream();
    this.stopAutoRefresh();
  }

  // ── WebSocket ─────────────────────────────────────────────────────────────

  private startStream(namespace: string, pod: string): void {
    this.stopStream();
    this.logs = [];
    this.wsActive = true;
    this.loadingLogs = false;

    this.logsSub = this.socketService
      .streamLogs(namespace, pod, this.refreshInterval)
      .subscribe({
        next: ({ lines }: { lines: { ts: string; line: string }[] }) => {
          this.logs.push(...lines);
        },
        error: (err: any) => {
          console.warn('[WS Logs] Erreur, bascule sur REST:', err);
          this.wsActive = false;
          this.startAutoRefresh();
        }
      });
  }

  private stopStream(): void {
    this.logsSub?.unsubscribe();
    this.socketService.disconnect('/logs');
    this.wsActive = false;
  }

  stopStreamPublic(): void {
    this.stopStream();
    this.logs = [];
  }

  // ── Auto-refresh REST (fallback) ──────────────────────────────────────────

  startAutoRefresh(): void {
    this.stopAutoRefresh();
    if (!this.autoRefresh) return;
    this.autoRefreshTimer = setInterval(() => {
      if (this.selectedNamespace && !this.loadingLogs) {
        this.loadLogs(false);
      }
    }, this.refreshInterval * 1000);
  }

  stopAutoRefresh(): void {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
      this.autoRefreshTimer = null;
    }
  }

  toggleAutoRefresh(): void {
    if (this.autoRefresh) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
  }

  onIntervalChange(): void {
    if (this.autoRefresh) {
      this.startAutoRefresh();
    }
  }

  // ── Namespaces / Pods ─────────────────────────────────────────────────────

  loadNamespaces(): void {
    this.loadingNamespaces = true;

    // ✅ Utilise la route backend qui filtre selon le rôle
    this.logsService.getAccessibleNamespaces().subscribe({
      next: (data: any) => {
        this.namespaces = (data.namespaces || []).sort();
        this.loadingNamespaces = false;
      },
      error: () => {
        this.loadingNamespaces = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger les namespaces'
        });
      }
    });
  }

  onNamespaceChange(): void {
    this.selectedPod = '';
    this.pods = [];
    this.podOptions = [];
    this.logs = [];
    this.stopStream();
    this.stopAutoRefresh();
    if (!this.selectedNamespace) return;

    this.loadingPods = true;
    this.k8sService.getPodsByNamespace(this.selectedNamespace).subscribe({
      next: (pods: any[]) => {
        this.pods = pods;
        this.podOptions = [
          { label: 'Tous les pods', value: '' },
          ...pods.map((p: any) => ({ label: p.name, value: p.name }))
        ];
        this.loadingPods = false;
        this.loadLogs(true);
      },
      error: () => {
        this.loadingPods = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger les pods'
        });
      }
    });
  }

  onPodChange(): void {
    this.logs = [];
    if (!this.selectedNamespace) return;

    if (this.selectedPod) {
      this.stopAutoRefresh();
      this.startStream(this.selectedNamespace, this.selectedPod);
    } else {
      this.stopStream();
      this.loadLogs(true);
      this.startAutoRefresh();
    }
  }

  // ── Chargement initial REST ───────────────────────────────────────────────

  loadLogs(showToast: boolean = false): void {
    if (!this.selectedNamespace) {
      if (showToast) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Attention',
          detail: 'Veuillez sélectionner un namespace'
        });
      }
      return;
    }

    this.loadingLogs = true;
    this.logs = [];

    const request$ = this.selectedPod
      ? this.logsService.getPodLogs(this.selectedNamespace, this.selectedPod)
      : this.logsService.getNamespaceLogs(this.selectedNamespace);

    request$.subscribe({
      next: (data: any) => {
        this.logs = data.logs || [];
        this.loadingLogs = false;
        if (this.selectedPod) {
          this.startStream(this.selectedNamespace, this.selectedPod);
        } else {
          this.startAutoRefresh();
        }
      },
      error: (err: any) => {
        this.loadingLogs = false;
        // ✅ Gère le 403 si le developer tente d'accéder à un namespace non autorisé
        if (err?.status === 403) {
          this.messageService.add({
            severity: 'warn',
            summary: 'Accès refusé',
            detail: 'Vous n\'avez pas accès aux logs de ce namespace'
          });
        } else if (showToast) {
          this.messageService.add({
            severity: 'error',
            summary: 'Erreur',
            detail: 'Impossible de récupérer les logs'
          });
        }
      }
    });
  }

  // ── Formatage ─────────────────────────────────────────────────────────────

  getLogsText(): string {
    return this.logs.map((entry: any) => this.formatLogEntry(entry)).join('\n');
  }

  formatLogEntry(entry: any): string {
    if (entry.ts !== undefined && entry.line !== undefined) {
      return entry.line;
    }
    const ts = entry.timestamp ?? entry.ts;
    let date: Date;
    try {
      date = new Date(Math.floor(Number(BigInt(ts) / BigInt(1_000_000))));
    } catch {
      date = new Date();
    }
    return `[${date.toLocaleString('fr-TN', { timeZone: 'Africa/Tunis' })}] ${entry.line}`;
  }
}