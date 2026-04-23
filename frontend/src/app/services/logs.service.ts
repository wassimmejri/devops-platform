import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class LogsService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getPodLogs(namespace: string, podName: string, limit: number = 50) {
    return this.http.get<any>(`${this.apiUrl}/logs/pods/${namespace}/${podName}`, {
      params: { limit: limit.toString() }
    });
  }

  getNamespaceLogs(namespace: string, limit: number = 500) {
    return this.http.get<any>(`${this.apiUrl}/logs/namespace/${namespace}`, {
      params: { limit: limit.toString() }
    });
  }
}