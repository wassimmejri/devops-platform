import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class MetricsService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getPodMetrics(namespace?: string) {
    let url = `${this.apiUrl}/metrics/pods`;
    if (namespace) url += `?namespace=${namespace}`;
    return this.http.get<any[]>(url);
  }

  getNodeMetrics() {
    return this.http.get<any[]>(`${this.apiUrl}/metrics/nodes`);
  }
}