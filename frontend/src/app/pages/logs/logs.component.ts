import { Component, OnInit, OnDestroy } from '@angular/core';
import { ProjectService } from '../../services/project.service';
import { K8sService } from '../../services/k8s.service';
import { LogsService } from '../../services/logs.service';
import { SocketService } from '../../services/socket.service';
import { MessageService } from 'primeng/api';
import { Subscription } from 'rxjs';

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

  autoRefresh = true;
  refreshInterval = 10;
  private autoRefreshTimer: any = null;

  constructor(
    private projectService: ProjectService,
    private k8sService: K8sService,
    private logsService: LogsService,
    private socketService: SocketService,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
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

  // ← méthode publique appelée par le bouton "Arrêter" du template
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
    this.k8sService.getPods().subscribe({
      next: (pods: any[]) => {
        const clusterNamespaces = [...new Set(pods.map(p => p.namespace).filter(Boolean))];
        this.projectService.getProjects().subscribe({
          next: (projects: any[]) => {
            const projectNamespaces = projects.map(p => p.k8s_namespace).filter(Boolean);
            this.namespaces = [...new Set([...clusterNamespaces, ...projectNamespaces])].sort();
            this.loadingNamespaces = false;
          },
          error: () => {
            this.namespaces = clusterNamespaces.sort();
            this.loadingNamespaces = false;
          }
        });
      },
      error: () => {
        this.loadingNamespaces = false;
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les namespaces' });
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
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les pods' });
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
        this.messageService.add({ severity: 'warn', summary: 'Attention', detail: 'Veuillez sélectionner un namespace' });
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
      error: () => {
        this.loadingLogs = false;
        if (showToast) {
          this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de récupérer les logs' });
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
  // toLocaleString avec timezone explicite
  return `[${date.toLocaleString('fr-TN', { timeZone: 'Africa/Tunis' })}] ${entry.line}`;
}
}