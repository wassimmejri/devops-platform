import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { LoginComponent } from './pages/login/login.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { ProjectsComponent } from './pages/projects/projects.component';
import { MicroservicesComponent } from './pages/microservices/microservices.component';
import { DeploymentsComponent } from './pages/deployments/deployments.component';
import { AuthGuard } from './guards/auth.guard';
import { ClusterComponent } from './pages/cluster/cluster.component';
import { LogsComponent } from './pages/logs/logs.component';
import { AlertsComponent } from './pages/alerts/alerts.component';
import { RoleGuard } from './guards/role.guard';
import { UsersComponent } from './pages/users/users.component';

const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },

  // Dashboard : accessible à tout utilisateur authentifié
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [AuthGuard]
  },

  // Projets : accessible aux deux rôles (le backend filtre par propriétaire)
  {
    path: 'projects',
    component: ProjectsComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'projects/:id/microservices',
    component: MicroservicesComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'microservices/:id/deployments',
    component: DeploymentsComponent,
    canActivate: [AuthGuard]
  },

  // Cluster : réservé aux administrateurs DevOps
  {
    path: 'cluster',
    component: ClusterComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['admin-devops'] }
  },

  // Logs : accessible à tout utilisateur authentifié
  {
    path: 'logs',
    component: LogsComponent,
    canActivate: [AuthGuard]
  },

  // Alertes : accessible à tout utilisateur authentifié (lecture seule)
  {
    path: 'alerts',
    component: AlertsComponent,
    canActivate: [AuthGuard]
  },
  {
  path: 'admin/users',
  component: UsersComponent,
  canActivate: [AuthGuard, RoleGuard],
  data: { roles: ['admin-devops'] }
},

  // Redirection par défaut
  { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }