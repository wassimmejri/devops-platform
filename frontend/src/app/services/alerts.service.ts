import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AlertsService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getAlerts() {
    return this.http.get<any[]>(`${this.apiUrl}/alerts/`);
  }

  getAlertGroups() {
    return this.http.get<any[]>(`${this.apiUrl}/alerts/groups`);
  }
}