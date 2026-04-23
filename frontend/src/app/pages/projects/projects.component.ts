import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ProjectService } from '../../services/project.service';
import { MessageService, ConfirmationService } from 'primeng/api';

@Component({
  selector: 'app-projects',
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.scss']
})
export class ProjectsComponent implements OnInit {

  projects: any[] = [];
  loading: boolean = false;
  showCreateDialog: boolean = false;

  newProject = {
    name: '',
    description: '',
    github_url: '',
    github_branch: 'main'
  };

  constructor(
    private projectService: ProjectService,
    private router: Router,
    private messageService: MessageService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.loadProjects();
  }

  loadProjects(): void {
    this.loading = true;
    this.projectService.getProjects().subscribe({
      next: (data) => {
        this.projects = data;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger les projets'
        });
      }
    });
  }

  createProject(): void {
    if (!this.newProject.name) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Attention',
        detail: 'Le nom du projet est obligatoire'
      });
      return;
    }

    this.projectService.createProject(this.newProject).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Succès',
          detail: 'Projet créé avec succès'
        });
        this.showCreateDialog = false;
        this.newProject = { name: '', description: '', github_url: '', github_branch: 'main' };
        this.loadProjects();
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de créer le projet'
        });
      }
    });
  }

  deleteProject(event: Event, id: number): void {
    this.confirmationService.confirm({
      target: event.target as EventTarget,
      message: 'Supprimer ce projet ? Tous ses microservices seront supprimés.',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.projectService.deleteProject(id).subscribe({
          next: () => {
            this.messageService.add({
              severity: 'success',
              summary: 'Supprimé',
              detail: 'Projet supprimé'
            });
            this.loadProjects();
          },
          error: () => {
            this.messageService.add({
              severity: 'error',
              summary: 'Erreur',
              detail: 'Impossible de supprimer'
            });
          }
        });
      }
    });
  }

  goToMicroservices(projectId: number): void {
    this.router.navigate(['/projects', projectId, 'microservices']);
  }
}