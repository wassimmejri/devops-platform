import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { K8sService } from '../../services/k8s.service';
import { MetricsService } from '../../services/metrics.service';
import { SocketService } from '../../services/socket.service';
import { MessageService } from 'primeng/api';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-cluster',
  templateUrl: './cluster.component.html',
  styleUrls: ['./cluster.component.scss']
})
export class ClusterComponent implements OnInit, OnDestroy {

  nodes: any[] = [];
  pods: any[] = [];
  nodeMetrics: any[] = [];

  loadingNodes = false;
  loadingPods = false;

  podSearch = '';
  podStatusFilter = '';

  selectedPod: any = null;
  showLogsDialog = false;
  podLogs = '';
  loadingLogs = false;

  autoRefresh = true;
  refreshInterval = 30;
  private refreshTimer: any = null;

  private metricsSub?: Subscription;
  private podsSub?: Subscription;

  constructor(
    private k8sService: K8sService,
    private metricsService: MetricsService,
    private socketService: SocketService,
    private messageService: MessageService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadNodes();
    this.loadNodeMetrics();
    this.loadPods();

    // ── Métriques CPU/RAM en temps réel ──
    this.metricsSub = this.socketService.watchMetrics(10).subscribe({
      next: (data: any) => {
        this.nodeMetrics = this.mergeMetrics(data);
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('[WS Metrics]', err)
    });

    // ── Pods en temps réel ──
    this.podsSub = this.socketService.watchPods('').subscribe({
      next: (event: any) => {
        this.applyPodEvent(event);
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('[WS Pods]', err)
    });
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
    this.metricsSub?.unsubscribe();
    this.podsSub?.unsubscribe();
    this.socketService.disconnect('/metrics');
    this.socketService.disconnect('/pods');
  }

  // ── Merge métriques Prometheus ────────────────────────────────────────────

  private mergeMetrics(data: any): any[] {
    const cpuResults = data?.cpu?.data?.result || [];
    const ramResults = data?.ram?.data?.result || [];
    return cpuResults.map((cpuItem: any) => {
      const instance = cpuItem.metric?.instance || '';
      const ramItem  = ramResults.find((r: any) => r.metric?.instance === instance);
      return {
        instance,
        cpu_usage: parseFloat(cpuItem.value?.[1] || '0'),
        ram_usage: parseFloat(ramItem?.value?.[1] || '0'),
      };
    });
  }

  // ── Apply pod event ───────────────────────────────────────────────────────

  private applyPodEvent(event: any): void {
    switch (event.event) {
      case 'ADDED':
        if (!this.pods.find(p => p.name === event.name)) {
          this.pods = [...this.pods, {
            name:      event.name,
            namespace: event.namespace,
            status:    event.status,
            ready:     event.ready,
            restarts:  event.restarts,
            node:      event.node,
          }];
        }
        break;
      case 'MODIFIED':
        this.pods = this.pods.map(p =>
          p.name === event.name
            ? { ...p, status: event.status, ready: event.ready, restarts: event.restarts }
            : p
        );
        break;
      case 'DELETED':
        this.pods = this.pods.filter(p => p.name !== event.name);
        break;
    }
  }

  // ── Auto-refresh REST (fallback nodes/métriques) ──────────────────────────

  startAutoRefresh(): void {
    this.stopAutoRefresh();
    if (!this.autoRefresh) return;
    this.refreshTimer = setInterval(() => {
      this.loadNodes();
      this.loadNodeMetrics();
    }, this.refreshInterval * 1000);
  }

  stopAutoRefresh(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  toggleAutoRefresh(): void {
    this.autoRefresh ? this.startAutoRefresh() : this.stopAutoRefresh();
  }

  loadAll(): void {
    this.loadNodes();
    this.loadPods();
    this.loadNodeMetrics();
  }

  loadNodes(): void {
    this.loadingNodes = true;
    this.k8sService.getNodes().subscribe({
      next: (data) => { this.nodes = data; this.loadingNodes = false; },
      error: () => {
        this.loadingNodes = false;
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les nœuds' });
      }
    });
  }

  loadPods(): void {
    this.loadingPods = true;
    this.k8sService.getPods().subscribe({
      next: (data) => { this.pods = data; this.loadingPods = false; },
      error: () => {
        this.loadingPods = false;
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les pods' });
      }
    });
  }

  loadNodeMetrics(): void {
    this.metricsService.getNodeMetrics().subscribe({
      next: (data) => { this.nodeMetrics = data; },
      error: (err) => { console.warn('Erreur métriques Prometheus:', err); this.nodeMetrics = []; }
    });
  }

  getNodeUsage(node: any): { cpuUsage: number | null; ramUsage: number | null } {
    if (!node || !node.ip) return { cpuUsage: null, ramUsage: null };
    const metric = this.nodeMetrics.find(m => m.instance?.startsWith(node.ip));
    return { cpuUsage: metric?.cpu_usage ?? null, ramUsage: metric?.ram_usage ?? null };
  }

  viewLogs(pod: any): void {
    this.selectedPod = pod;
    this.showLogsDialog = true;
    this.loadingLogs = true;
    this.podLogs = '';
    this.k8sService.getPodLogs(pod.namespace, pod.name).subscribe({
      next: (data: any) => { this.podLogs = data.logs; this.loadingLogs = false; },
      error: () => { this.loadingLogs = false; this.podLogs = 'Impossible de récupérer les logs'; }
    });
  }

  restartPod(pod: any): void {
    this.k8sService.restartPod(pod.namespace, pod.name).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Succès', detail: `Pod ${pod.name} redémarré` });
      },
      error: () => {
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de redémarrer le pod' });
      }
    });
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'Running': return 'success';
      case 'Pending': return 'warning';
      case 'Failed':  return 'danger';
      default:        return 'info';
    }
  }

  getNodeSeverity(status: string): string {
    return status === 'Ready' ? 'success' : 'danger';
  }

  get runningPods() { return this.pods.filter(p => p.status === 'Running').length; }
  get pendingPods() { return this.pods.filter(p => p.status === 'Pending').length; }
  get failedPods()  { return this.pods.filter(p => p.status === 'Failed').length; }

  get filteredPods() {
    const search = this.podSearch.trim().toLowerCase();
    return this.pods.filter(pod => {
      const matchesSearch = !search || [pod.name, pod.namespace, pod.status]
        .filter(Boolean).some(v => v.toString().toLowerCase().includes(search));
      const matchesStatus = !this.podStatusFilter || pod.status === this.podStatusFilter;
      return matchesSearch && matchesStatus;
    });
  }

  getNodeRamGB(node: any): string {
    const bytes = this.parseMemoryValue(node.memory);
    return isFinite(bytes) ? (bytes / 1024 / 1024).toFixed(0) : '0';
  }

  private parseMemoryValue(memory: any): number {
    if (memory == null) return 0;
    if (typeof memory === 'number') return Number.isFinite(memory) ? memory : 0;
    const value = memory.toString().trim();
    if (!value) return 0;
    const numeric = parseFloat(value.replace(/,/g, '.'));
    if (!Number.isNaN(numeric) && /^\s*[\d.,]+\s*$/.test(value)) return numeric;
    const normalized = value.toUpperCase().replace(/B$/, '').trim();
    const match = normalized.match(/^([\d.]+)\s*(K|KI|M|MI|G|GI|T|TI)$/);
    if (!match) return Number.isFinite(numeric) ? numeric : 0;
    const amount = parseFloat(match[1]);
    if (Number.isNaN(amount)) return 0;
    switch (match[2]) {
      case 'K': case 'KI': return amount * 1024;
      case 'M': case 'MI': return amount * 1024 ** 2;
      case 'G': case 'GI': return amount * 1024 ** 3;
      case 'T': case 'TI': return amount * 1024 ** 4;
      default: return numeric;
    }
  }
}