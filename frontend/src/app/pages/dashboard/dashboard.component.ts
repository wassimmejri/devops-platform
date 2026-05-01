import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { ProjectService } from '../../services/project.service';
import { K8sService } from '../../services/k8s.service';
import { MetricsService } from '../../services/metrics.service';
import { AuthService } from '../../services/auth.service';
import { SocketService } from '../../services/socket.service';
import { MicroserviceService } from '../../services/microservice.service';
import { MessageService, ConfirmationService } from 'primeng/api';
import { Subscription } from 'rxjs';
import 'chartjs-adapter-date-fns';
@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {

  projects: any[] = [];
  pods: any[] = [];
  nodes: any[] = [];
  nodeMetrics: any[] = [];
  recentDeployments: any[] = [];

  podSearch = '';
  podStatusFilter = '';
  projectSearch = '';

  loadingProjects = false;
  loadingPods = false;
  loadingNodes = false;
  loadingDeployments = false;

  lastRefresh = '';
  private isManualRefresh = false;

  private metricsSub?: Subscription;
  private podsSub?: Subscription;
  private deploymentsSub?: Subscription;
  private alertsSub?: Subscription;


  cpuChartData: any;
  cpuChartOptions: any;
  ramChartData: any;
  ramChartOptions: any;
  podStatusChartData: any;
  podStatusChartOptions: any;

  historyChartData: any = null;
  historyChartOptions: any;

  alertsData: any = { alerts: [], summary: { critical: 0, warning: 0, info: 0, total: 0 } };
  showAlertsPanel: boolean = false;

  constructor(
    private router: Router,
    private projectService: ProjectService,
    private k8sService: K8sService,
    private metricsService: MetricsService,
    private authService: AuthService,
    private socketService: SocketService,
    private microserviceService: MicroserviceService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadAll();

    this.metricsSub = this.socketService.watchMetrics(10).subscribe({
      next: (data: any) => {
        this.nodeMetrics = this.mergeMetrics(data);
        this.updateLastRefresh();
        this.buildCpuChart();
        this.buildRamChart();
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('[WS Metrics] erreur:', err)
    });

    this.podsSub = this.socketService.watchPods('').subscribe({
      next: (event: any) => {
        this.applyPodEvent(event);
        this.buildPodStatusChart();
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('[WS Pods] erreur:', err)
    });

    // ── AJOUT : WebSocket pour les déploiements ──────────────────────
    this.deploymentsSub = this.socketService.watchDeployments().subscribe({
      next: (update: any) => {
        console.log('[WS] Deployment update reçu', update);
        this.loadRecentDeployments();
      },
      error: (err) => console.warn('[WS Deployments] erreur:', err)
    });

     // ── AJOUT : WebSocket pour l'historique CPU/RAM ──────────────────
    this.socketService.watchHistory().subscribe((data: any) => {
      this.updateHistoryChart(data);
      this.cdr.detectChanges();
    });
    this.alertsSub = this.socketService.watchAlerts(15).subscribe({
  next: (data: any) => {
    this.alertsData = data;
    this.cdr.detectChanges();
  },
  error: (err) => console.warn('[WS Alerts] erreur:', err)
});
  
  }

  ngOnDestroy(): void {
    this.metricsSub?.unsubscribe();
    this.podsSub?.unsubscribe();
    this.deploymentsSub?.unsubscribe();               // ← AJOUTER
    this.socketService.disconnect('/metrics');
    this.socketService.disconnect('/pods');
    this.socketService.disconnect('/deployments'); 
    this.alertsSub?.unsubscribe();
    this.socketService.disconnect('/alerts');
    // ← AJOUTER
  }

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

  loadAll(): void {
    this.updateLastRefresh();
    this.loadProjects();
    this.loadPods();
    this.loadNodes();
    this.loadNodeMetrics();
    this.loadRecentDeployments();

    if (this.isManualRefresh) {
      this.messageService.add({
        severity: 'success',
        summary: 'Synchronisation terminée',
        detail: 'Les données du cluster ont été actualisées.',
        life: 3000
      });
      this.isManualRefresh = false;
    }
  }

  updateLastRefresh(): void {
    this.lastRefresh = new Date().toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  }

  loadProjects(): void {
    this.loadingProjects = true;
    this.projectService.getProjects().subscribe({
      next: (data) => {
        this.projects = data;
        this.loadingProjects = false;
      },
      error: () => {
        this.loadingProjects = false;
      }
    });
  }

  loadRecentDeployments(): void {
    this.loadingDeployments = true;
    this.microserviceService.getAllRecentDeployments().subscribe({
      next: (data) => {
        this.recentDeployments = data.slice(0, 5);
        this.loadingDeployments = false;
      },
      error: () => {
        this.loadingDeployments = false;
        this.recentDeployments = [];
      }
    });
  }

  loadPods(): void {
    this.loadingPods = true;
    this.k8sService.getPods().subscribe({
      next: (data) => {
        this.pods = data;
        this.loadingPods = false;
        this.buildPodStatusChart();
      },
      error: () => { this.loadingPods = false; }
    });
  }

  loadNodes(): void {
    this.loadingNodes = true;
    this.k8sService.getNodes().subscribe({
      next: (data) => {
        this.nodes = data;
        this.loadingNodes = false;
      },
      error: () => { this.loadingNodes = false; }
    });
  }

  loadNodeMetrics(): void {
    this.metricsService.getNodeMetrics().subscribe({
      next: (data) => {
        this.nodeMetrics = data;
        this.buildCpuChart();
        this.buildRamChart();
      },
      error: (err) => console.warn('Erreur métriques Prometheus:', err)
    });
  }

  // ── Computed ──────────────────────────────────────────

  get avgCpuUsage(): number {
    if (!this.nodeMetrics.length) return 0;
    return this.nodeMetrics.reduce((acc, m) => acc + (m.cpu_usage || 0), 0) / this.nodeMetrics.length;
  }

  get avgRamUsage(): number {
    if (!this.nodeMetrics.length) return 0;
    return this.nodeMetrics.reduce((acc, m) => acc + (m.ram_usage || 0), 0) / this.nodeMetrics.length;
  }

  get runningPods()   { return this.pods.filter(p => p.status === 'Running').length; }
  get pendingPods()   { return this.pods.filter(p => p.status === 'Pending').length; }
  get failedPods()    { return this.pods.filter(p => p.status === 'Failed').length; }
  get readyNodes()    { return this.nodes.filter(n => n.status === 'Ready').length; }
  get totalCpuCores() { return this.nodes.reduce((sum, n) => sum + (Number(n.cpu) || 0), 0); }
  get totalRamGB()    { return this.nodes.reduce((sum, n) => sum + (this.parseMemoryValue(n.memory) / 1024 / 1024), 0); }

  get filteredPods() {
    const search = this.podSearch.trim().toLowerCase();
    return this.pods.filter(pod => {
      const matchesSearch = !search || [pod.name, pod.namespace, pod.status]
        .filter(Boolean).some(v => v.toString().toLowerCase().includes(search));
      const matchesStatus = !this.podStatusFilter || pod.status === this.podStatusFilter;
      return matchesSearch && matchesStatus;
    });
  }

  get filteredProjects() {
    const search = this.projectSearch.trim().toLowerCase();
    return this.projects.filter(p => {
      const name = p.name?.toString().toLowerCase() || '';
      const ns   = p.k8s_namespace?.toString().toLowerCase() || '';
      return !search || name.includes(search) || ns.includes(search);
    });
  }

  // ── Charts ────────────────────────────────────────────

  buildPodStatusChart(): void {
    this.podStatusChartData = {
      labels: ['Running', 'Pending', 'Failed'],
      datasets: [{
        data: [this.runningPods, this.pendingPods, this.failedPods],
        backgroundColor: ['#00c864', '#f59e0b', '#ef4444'],
        borderWidth: 0
      }]
    };
    this.podStatusChartOptions = {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#7a9a8a', padding: 16, font: { family: 'JetBrains Mono', size: 11 } }
        }
      },
      cutout: '70%'
    };
  }

  buildCpuChart(): void {
    const labels: string[] = [];
    const data: number[]   = [];
    for (const node of this.nodes) {
      const usage = this.getNodeUsage(node);
      labels.push(node.name.split('-')[0]);
      data.push(usage.cpuUsage ?? 0);
    }
    this.cpuChartData = {
      labels,
      datasets: [{ label: 'CPU Usage (%)', data, backgroundColor: 'rgba(0,200,100,0.7)', borderRadius: 6 }]
    };
    this.cpuChartOptions = {
      responsive: true,
      plugins: { legend: { labels: { color: '#7a9a8a', font: { family: 'JetBrains Mono', size: 11 } } } },
      scales: {
        x: { ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a2a3a' } },
        y: { ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a2a3a' }, max: 100 }
      }
    };
  }

  buildRamChart(): void {
    const labels: string[] = [];
    const data: number[]   = [];
    for (const node of this.nodes) {
      const usage = this.getNodeUsage(node);
      labels.push(node.name.split('-')[0]);
      data.push(usage.ramUsage ?? 0);
    }
    this.ramChartData = {
      labels,
      datasets: [{ label: 'RAM Usage (%)', data, backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 6 }]
    };
    this.ramChartOptions = {
      responsive: true,
      plugins: { legend: { labels: { color: '#7a9a8a', font: { family: 'JetBrains Mono', size: 11 } } } },
      scales: {
        x: { ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a2a3a' } },
        y: { ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a2a3a' }, max: 100 }
      }
    };
  }

  // ── Helpers ───────────────────────────────────────────

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

  getNodeUsage(node: any): { cpuUsage: number | null; ramUsage: number | null } {
    if (!node?.ip) return { cpuUsage: null, ramUsage: null };
    const metric = this.nodeMetrics.find(m => m.instance?.startsWith(node.ip));
    return { cpuUsage: metric?.cpu_usage ?? null, ramUsage: metric?.ram_usage ?? null };
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'Running': return 'success';
      case 'Pending': return 'warning';
      case 'Failed':  return 'danger';
      default:        return 'info';
    }
  }

  getDeploymentSeverity(status: string): string {
    switch (status) {
      case 'success':  return 'success';
      case 'building': return 'warning';
      case 'failed':   return 'danger';
      default:         return 'info';
    }
  }

    getAlertSeverity(severity: string): string {
    switch (severity) {
      case 'critical': return 'danger';
      case 'warning': return 'warning';
      default: return 'info';
    }
  }

  getNodeRamGB(node: any): string {
    const bytes = this.parseMemoryValue(node.memory);
    return isFinite(bytes) ? (bytes / 1024 / 1024).toFixed(0) : '0';
  }

  getNodeSeverity(status: string): string {
    return status === 'Ready' ? 'success' : 'danger';
  }

  getTimeAgo(dateStr: string): string {
    if (!dateStr) return '—';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1)  return 'à l\'instant';
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return `${hrs}h`;
    return `${Math.floor(hrs / 24)}j`;
  }

  get currentUserName(): string {
    const user = this.getCurrentUser();
    return user?.full_name || user?.name || user?.email || 'Utilisateur';
  }

  goToProject(projectId: number): void {
    if (!projectId) return;
    this.router.navigate(['/projects', projectId, 'microservices']);
  }

  updateHistoryChart(data: any): void {
  const cpuPoints = (data.cpu || []).map((p: any) => ({ x: new Date(p[0] * 1000), y: p[1] }));
  const ramPoints = (data.ram || []).map((p: any) => ({ x: new Date(p[0] * 1000), y: p[1] }));

  this.historyChartData = {
    datasets: [
      {
        label: 'CPU (%)',
        data: cpuPoints,
        borderColor: '#00e5ff',
        backgroundColor: 'rgba(0,229,255,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0
      },
      {
        label: 'RAM (%)',
        data: ramPoints,
        borderColor: '#a78bfa',
        backgroundColor: 'rgba(139,92,246,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0
      }
    ]
  };

  this.historyChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#7a9a8a', font: { family: 'JetBrains Mono', size: 11 } } }
    },
    scales: {
      x: {
        type: 'time',
        time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
        grid: { color: '#1a2a3a' },
        ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } }
      },
      y: {
        grid: { color: '#1a2a3a' },
        ticks: { color: '#3a5a50', font: { family: 'JetBrains Mono', size: 10 } },
        max: 100
      }
    }
  };
}

  navigateTo(path: string): void { this.router.navigate([path]); }

  manualRefresh(): void {
    this.isManualRefresh = true;
    this.loadAll();
  }

  confirmLogout(event: Event): void {
    this.confirmationService.confirm({
      target: event.target as EventTarget,
      message: 'Voulez-vous vraiment vous déconnecter ?',
      icon: 'pi pi-sign-out',
      key: 'logout',
      accept: () => this.authService.logout()
    });
  }

  logout(): void { this.authService.logout(); }
  getCurrentUser(): any { return this.authService.getCurrentUser(); }
}