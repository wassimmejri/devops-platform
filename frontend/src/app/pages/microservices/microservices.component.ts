import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MicroserviceService } from '../../services/microservice.service';
import { ProjectService } from '../../services/project.service';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-microservices',
  templateUrl: './microservices.component.html',
  styleUrls: ['./microservices.component.scss']
})
export class MicroservicesComponent implements OnInit {

  projectId: number = 0;
  project: any = {};
  microservices: any[] = [];
  loading: boolean = false;
  showCreateDialog: boolean = false;

  newMicroservice = {
    name: '',
    image: '',
    port: 8080,
    replicas: 1,
    env_vars: {}
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private microserviceService: MicroserviceService,
    private projectService: ProjectService,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    this.projectId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadProject();
    this.loadMicroservices();
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

  deploy(microservice: any): void {
    this.microserviceService.deploy(microservice.id, 'latest').subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Déploiement lancé !',
          detail: `Pipeline Jenkins déclenché pour ${microservice.name}`
        });
        this.loadMicroservices();
      },
      error: (error) => {
        const detail = error?.error?.message || error?.message || 'Impossible de lancer le déploiement';
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail
        });
        console.error('Deploy error', error);
      }
    });
  }

  viewDeployments(microservice: any): void {
    this.router.navigate([`/microservices/${microservice.id}/deployments`]);
  }

  getStatusSeverity(status: string): string {
    switch (status) {
      case 'running': return 'success';
      case 'deploying': return 'warning';
      case 'error': return 'danger';
      default: return 'info';
    }
  }

  // Getters pour les statistiques
  get runningCount(): number {
    return this.microservices.filter(m => m.status === 'running').length;
  }

  get deployingCount(): number {
    return this.microservices.filter(m => m.status === 'deploying').length;
  }

  get errorCount(): number {
    return this.microservices.filter(m => m.status === 'error').length;
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}