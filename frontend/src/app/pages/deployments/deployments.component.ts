import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MicroserviceService } from '../../services/microservice.service';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-deployments',
  templateUrl: './deployments.component.html',
  styleUrls: ['./deployments.component.scss']
})
export class DeploymentsComponent implements OnInit {

  microserviceId: number = 0;
  deployments: any[] = [];
  loading: boolean = false;
  selectedDeployment: any = null;
  showLogsDialog: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private microserviceService: MicroserviceService,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    this.microserviceId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadDeployments();
  }

  loadDeployments(): void {
    this.loading = true;
    this.microserviceService.getDeployments(this.microserviceId).subscribe({
      next: (data) => {
        this.deployments = data;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger les déploiements'
        });
      }
    });
  }

  viewLogs(deployment: any): void {
    this.selectedDeployment = deployment;
    this.showLogsDialog = true;
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'success':   return 'success';
      case 'building':  return 'warning';
      case 'deploying': return 'warning';
      case 'failed':    return 'danger';
      default:          return 'info';
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'success':   return 'pi pi-check-circle';
      case 'building':  return 'pi pi-spin pi-spinner';
      case 'deploying': return 'pi pi-spin pi-spinner';
      case 'failed':    return 'pi pi-times-circle';
      default:          return 'pi pi-clock';
    }
  }

  getDuration(deployment: any): string {
    if (deployment.duration) return `${deployment.duration}s`;
    if (deployment.finished_at && deployment.created_at) {
      const diff = new Date(deployment.finished_at).getTime() - new Date(deployment.created_at).getTime();
      return `${Math.floor(diff / 1000)}s`;
    }
    return '—';
  }

  goBack(): void {
    this.router.navigate(['/projects']);
  }
}