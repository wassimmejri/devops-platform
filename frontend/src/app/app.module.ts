import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

// Pages
import { LoginComponent } from './pages/login/login.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { ProjectsComponent } from './pages/projects/projects.component';
import { MicroservicesComponent } from './pages/microservices/microservices.component';
import { DeploymentsComponent } from './pages/deployments/deployments.component';
import { SidebarComponent } from './pages/sidebar/sidebar.component';



// Components
import { NavbarComponent } from './components/navbar/navbar.component';

// PrimeNG Modules
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { ProgressBarModule } from 'primeng/progressbar';
import { MenuModule } from 'primeng/menu';
import { SidebarModule } from 'primeng/sidebar';
import { ChartModule } from 'primeng/chart';
import { BadgeModule } from 'primeng/badge';
import { AvatarModule } from 'primeng/avatar';
import { DropdownModule } from 'primeng/dropdown';
import { ConfirmDialogModule } from 'primeng/confirmdialog';

// Services
import { MessageService } from 'primeng/api';
import { ConfirmationService } from 'primeng/api';
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { StatusFilterPipe } from './pipes/status-filter.pipe';
import { ClusterComponent } from './pages/cluster/cluster.component';

import { TooltipModule } from 'primeng/tooltip';
import { RouterModule } from '@angular/router';
import { DeploymentFilterPipe } from './pipes/deployment-filter.pipe';

import { RefreshTokenInterceptor } from './interceptors/refresh-token.interceptor';
import { LogsComponent } from './pages/logs/logs.component';
import { LogsService } from './services/logs.service';
import { CheckboxModule } from 'primeng/checkbox';
import { AlertsComponent } from './pages/alerts/alerts.component';



@NgModule({
  declarations: [
    DeploymentFilterPipe,
    AppComponent,
    LoginComponent,
    DashboardComponent,
    ProjectsComponent,
    MicroservicesComponent,
    DeploymentsComponent,
    NavbarComponent,
    SidebarComponent,
    StatusFilterPipe,
    StatusFilterPipe,
    ClusterComponent,
    LogsComponent,
    AlertsComponent,  

  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    AppRoutingModule,
    // PrimeNG
    ButtonModule,
    InputTextModule,
    CardModule,
    TableModule,
    DialogModule,
    ToastModule,
    TagModule,
    ProgressBarModule,
    MenuModule,
    SidebarModule,
    ChartModule,
    BadgeModule,
    AvatarModule,
    DropdownModule,
    ConfirmDialogModule,
    TooltipModule,
    RouterModule,
    CheckboxModule

    
  ],
  providers: [
    MessageService,
    ConfirmationService,
    
    
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },
      { provide: HTTP_INTERCEPTORS, useClass: RefreshTokenInterceptor, multi: true }

  ],
  bootstrap: [AppComponent]
})
export class AppModule { }