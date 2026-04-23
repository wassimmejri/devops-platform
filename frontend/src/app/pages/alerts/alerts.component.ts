import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { AlertsService } from '../../services/alerts.service';
import { MessageService } from 'primeng/api';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-alerts',
  templateUrl: './alerts.component.html',
  styleUrls: ['./alerts.component.scss']
})
export class AlertsComponent implements OnInit, OnDestroy {

  alerts: any[] = [];
  summary = { critical: 0, warning: 0, info: 0, total: 0 };
  loading = true;
  wsActive = false;
  lastRefresh = '';

  severityFilter = '';
  nameFilter = '';

  private alertsSub?: Subscription;

  constructor(
    private socketService: SocketService,
    private alertsService: AlertsService,
    private messageService: MessageService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Chargement initial REST
    this.alertsService.getAlerts().subscribe({
      next: (data) => {
        this.alerts  = data;
        this.loading = false;
        this.computeSummary();
      },
      error: () => { this.loading = false; }
    });

    // WebSocket temps réel
    this.alertsSub = this.socketService.watchAlerts(15).subscribe({
      next: (data: any) => {
        this.alerts   = data.alerts  || [];
        this.summary  = data.summary || { critical: 0, warning: 0, info: 0, total: 0 };
        this.wsActive = true;
        this.lastRefresh = new Date().toLocaleTimeString();
        this.loading  = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.warn('[WS Alerts]', err);
        this.wsActive = false;
      }
    });
  }

  ngOnDestroy(): void {
    this.alertsSub?.unsubscribe();
    this.socketService.disconnect('/alerts');
  }

  private computeSummary(): void {
    this.summary = { critical: 0, warning: 0, info: 0, total: this.alerts.length };
    for (const alert of this.alerts) {
      const sev = alert.labels?.severity?.toLowerCase() || 'info';
      if (sev in this.summary) (this.summary as any)[sev]++;
    }
  }

  get filteredAlerts(): any[] {
    return this.alerts.filter(alert => {
      const matchSev  = !this.severityFilter ||
        alert.labels?.severity?.toLowerCase() === this.severityFilter;
      const matchName = !this.nameFilter ||
        alert.labels?.alertname?.toLowerCase()
          .includes(this.nameFilter.toLowerCase());
      return matchSev && matchName;
    });
  }

  getSeverityClass(severity: string): string {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'badge--critical';
      case 'warning':  return 'badge--warning';
      default:         return 'badge--info';
    }
  }

  getSeverityIcon(severity: string): string {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'pi-times-circle';
      case 'warning':  return 'pi-exclamation-triangle';
      default:         return 'pi-info-circle';
    }
  }

  getStatusClass(state: string): string {
    return state === 'firing' ? 'state--firing' : 'state--pending';
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('fr-TN', { timeZone: 'Africa/Tunis' });
  }

  clearFilters(): void {
    this.severityFilter = '';
    this.nameFilter     = '';
  }
}