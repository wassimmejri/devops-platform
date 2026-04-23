import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class K8sService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getNodes(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/k8s/nodes`);
  }

  getPods(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/k8s/pods`);
  }

  getPodsByNamespace(namespace: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/k8s/pods/${namespace}`);
  }

  getPodLogs(namespace: string, podName: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/k8s/pods/${namespace}/${podName}/logs`);
  }

  restartPod(namespace: string, podName: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/k8s/pods/${namespace}/${podName}/restart`, {});
  }

  getDeployments(namespace: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/k8s/deployments/${namespace}`);
  }

  scaleDeployment(namespace: string, name: string, replicas: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/k8s/deployments/${namespace}/${name}/scale`, { replicas });
  }
}