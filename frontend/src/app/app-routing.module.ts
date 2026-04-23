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

const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [AuthGuard]
  },
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
  { 
    path: 'cluster', 
    component: ClusterComponent, 
    canActivate: [AuthGuard] 
  },
  {
    path: 'logs',
    component: LogsComponent,
    canActivate: [AuthGuard]
  },
  { path: 'alerts', component: AlertsComponent },
  { path: '**', redirectTo: '/dashboard' } // ← toujours en dernier !
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }