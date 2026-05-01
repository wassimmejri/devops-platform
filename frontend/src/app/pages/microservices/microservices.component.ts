import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MicroserviceService } from '../../services/microservice.service';
import { ProjectService } from '../../services/project.service';
import { MessageService, ConfirmationService } from 'primeng/api';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

const PIPELINE_STAGES = [
  { key: 'verify',    label: 'Verify',    icon: 'pi-check-circle' },
  { key: 'namespace', label: 'Namespace', icon: 'pi-box' },
  { key: 'kaniko',    label: 'Build',     icon: 'pi-hammer' },
  { key: 'deploy',    label: 'Deploy',    icon: 'pi-cloud-upload' },
  { key: 'expose',    label: 'Expose',    icon: 'pi-wifi' },
  { key: 'verify2',   label: 'Verify',    icon: 'pi-check-square' },
];

@Component({
  selector: 'app-microservices',
  templateUrl: './microservices.component.html',
  styleUrls: ['./microservices.component.scss'],
})
export class MicroservicesComponent implements OnInit, OnDestroy {

  projectId: number = 0;
  project: any = {};
  microservices: any[] = [];
  loading: boolean = false;
  showCreateDialog: boolean = false;

  newMicroservice = {
    name: '', image: '', port: 8080, replicas: 1, env_vars: {}
  };

  // ── Pipeline stages ───────────────────────────────────
  pipelineStages = PIPELINE_STAGES;
  activeStages   = new Map<number, number>();

  // ── Logs dialog (statique fallback) ───────────────────
  showLogsDialog   = false;
  logsDialogTitle  = '';
  logsContent      = '';
  loadingLogs      = false;

  // ── Terminal dialog (WebSocket live) ──────────────────
  showTerminalDialog = false;
  terminalJobName    = '';
  terminalBuildNum   = 0;

  // ── Polling ───────────────────────────────────────────
  private pollingSubs = new Map<number, Subscription>();
  private stageSubs   = new Map<number, any>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private microserviceService: MicroserviceService,
    private projectService: ProjectService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.projectId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadProject();
    this.loadMicroservices();
  }

  ngOnDestroy(): void {
    this.pollingSubs.forEach(sub => sub.unsubscribe());
    this.stageSubs.forEach(t => clearInterval(t));
  }

  loadProject(): void {
    this.projectService.getProjects().subscribe({
      next: (projects) => {
        this.project = projects.find(p => p.id === this.projectId) || {};
      }
    });
  }

  loadMicroservices(): void {
    this.loading = true;
    this.microserviceService.getMicroservices(this.projectId).subscribe({
      next: (data) => {
        this.microservices = data;
        this.loading = false;
        this.microservices
          .filter(m => m.status === 'deploying')
          .forEach(m => {
            this.startStageAnimation(m.id);
            this.startPolling(m.id);
          });
      },
      error: () => {
        this.loading = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger les microservices'
        });
      }
    });
  }

  createMicroservice(): void {
    if (!this.newMicroservice.name) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Attention',
        detail: 'Le nom est obligatoire'
      });
      return;
    }
    this.microserviceService.createMicroservice(this.projectId, this.newMicroservice).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Succès',
          detail: 'Microservice ajouté avec succès'
        });
        this.showCreateDialog = false;
        this.newMicroservice = { name: '', image: '', port: 8080, replicas: 1, env_vars: {} };
        this.loadMicroservices();
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de créer le microservice'
        });
      }
    });
  }

  // ── Confirmation avant déploiement ────────────────────
  confirmDeploy(microservice: any, event: Event): void {
    this.confirmationService.confirm({
      header: 'Confirmer le déploiement',
      message: `Déployer <strong>${microservice.name}</strong> sur <strong>${this.project.k8s_namespace}</strong> ?`,
      icon: 'pi pi-cloud-upload',
      acceptLabel: 'Déployer',
      rejectLabel: 'Annuler',
      acceptButtonStyleClass: 'p-button-warning',
      rejectButtonStyleClass: 'p-button-secondary',
      accept: () => this.deploy(microservice),
    });
  }

  deploy(microservice: any): void {
    this.microserviceService.deploy(microservice.id, 'latest').subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Déploiement lancé !',
          detail: `Pipeline Jenkins déclenché pour ${microservice.name}`
        });
        const ms = this.microservices.find(m => m.id === microservice.id);
        if (ms) ms.status = 'deploying';
        this.startStageAnimation(microservice.id);
        this.startPolling(microservice.id);
      },
      error: (error) => {
        const detail = error?.error?.message || error?.message || 'Impossible de lancer le déploiement';
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail });
        console.error('Deploy error', error);
      }
    });
  }

  // ── Logs Jenkins (Terminal WebSocket live) ────────────
viewJenkinsLogs(microservice: any): void {
  this.microserviceService
    .getLastBuildInfo(microservice.jenkins_job_name)
    .subscribe({
      next: (data: any) => {
        if (data.build_number) {
          if (data.building === true) {
            // Build EN COURS → Terminal WebSocket live
            this.terminalJobName    = microservice.jenkins_job_name;
            this.terminalBuildNum   = data.build_number;
            this.showTerminalDialog = true;
          } else {
            // Build TERMINÉ → Logs statiques
            this._showStaticLogs(microservice);
          }
        } else {
          this._showStaticLogs(microservice);
        }
      },
      error: () => {
        this._showStaticLogs(microservice);
      }
    });
}

  // ── Fallback : logs statiques ─────────────────────────
  private _showStaticLogs(microservice: any): void {
    this.logsDialogTitle = `Logs Jenkins — ${microservice.name}`;
    this.logsContent     = '';
    this.loadingLogs     = true;
    this.showLogsDialog  = true;

    this.microserviceService
      .getJenkinsLogs(microservice.jenkins_job_name)
      .subscribe({
        next: (data: any) => {
          this.logsContent = data.logs || 'Aucun log disponible.';
          this.loadingLogs = false;
        },
        error: () => {
          this.logsContent = '❌ Impossible de récupérer les logs Jenkins.';
          this.loadingLogs = false;
        }
      });
  }

  // ── Fermer terminal dialog ────────────────────────────
  closeTerminalDialog(): void {
    this.showTerminalDialog = false;
    this.terminalJobName    = '';
    this.terminalBuildNum   = 0;
  }

  // ── Stage animation ───────────────────────────────────
  private startStageAnimation(microserviceId: number): void {
    this.stopStageAnimation(microserviceId);
    this.activeStages.set(microserviceId, 0);
    const timer = setInterval(() => {
      const current = this.activeStages.get(microserviceId) ?? 0;
      if (current < this.pipelineStages.length - 1) {
        this.activeStages.set(microserviceId, current + 1);
      }
    }, 20000);
    this.stageSubs.set(microserviceId, timer);
  }

  private stopStageAnimation(microserviceId: number): void {
    const timer = this.stageSubs.get(microserviceId);
    if (timer) { clearInterval(timer); this.stageSubs.delete(microserviceId); }
  }

  getStageStatus(microserviceId: number, stageIndex: number, msStatus: string): string {
    if (msStatus === 'running') return 'done';
    if (msStatus === 'error') {
      const active = this.activeStages.get(microserviceId) ?? 0;
      if (stageIndex < active)   return 'done';
      if (stageIndex === active) return 'error';
      return 'pending';
    }
    const active = this.activeStages.get(microserviceId) ?? 0;
    if (stageIndex < active)   return 'done';
    if (stageIndex === active) return 'active';
    return 'pending';
  }

  isDeploying(microservice: any): boolean {
    return microservice.status === 'deploying';
  }

  showLogsBtn(microservice: any): boolean {
    return ['deploying', 'error', 'running'].includes(microservice.status)
        && !!microservice.jenkins_job_name;
  }

  // ── Polling ───────────────────────────────────────────
  private startPolling(microserviceId: number): void {
    this.stopPolling(microserviceId);
    const sub = interval(5000).pipe(
      switchMap(() => this.microserviceService.syncStatus(microserviceId)),
      takeWhile(
        (res: any) => res.building === true || res.microservice_status === 'deploying',
        true
      )
    ).subscribe({
      next: (res: any) => {
        const ms = this.microservices.find(m => m.id === microserviceId);
        if (ms) ms.status = res.microservice_status;
        if (!res.building && res.microservice_status !== 'deploying') {
          this.stopPolling(microserviceId);
          this.stopStageAnimation(microserviceId);
          if (res.microservice_status === 'running') {
            this.activeStages.set(microserviceId, this.pipelineStages.length);
          }
          const success = res.microservice_status === 'running';
          this.messageService.add({
            severity: success ? 'success' : 'error',
            summary:  success ? '✅ Déploiement réussi' : '❌ Déploiement échoué',
            detail:   `Build #${res.build_number} — ${res.microservice_status}`,
            life: 6000
          });
        }
      },
      error: () => this.stopPolling(microserviceId)
    });
    this.pollingSubs.set(microserviceId, sub);
  }

  private stopPolling(microserviceId: number): void {
    this.pollingSubs.get(microserviceId)?.unsubscribe();
    this.pollingSubs.delete(microserviceId);
  }

  viewDeployments(microservice: any): void {
    this.router.navigate([`/microservices/${microservice.id}/deployments`]);
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'running':   return 'success';
      case 'deploying': return 'warning';
      case 'error':     return 'danger';
      default:          return 'info';
    }
  }

  get runningCount():   number { return this.microservices.filter(m => m.status === 'running').length; }
  get deployingCount(): number { return this.microservices.filter(m => m.status === 'deploying').length; }
  get errorCount():     number { return this.microservices.filter(m => m.status === 'error').length; }

  goBack(): void { this.router.navigate(['/dashboard']); }
}