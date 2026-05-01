import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class MicroserviceService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getMicroservices(projectId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/projects/${projectId}/microservices`);
  }

  createMicroservice(projectId: number, microservice: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/projects/${projectId}/microservices`, microservice);
  }

  deleteMicroservice(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/microservices/${id}`);
  }

  deploy(microserviceId: number, version: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/jenkins/microservices/${microserviceId}/deploy`,
      { version }
    );
  }

  getDeployments(microserviceId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/microservices/${microserviceId}/deployments`);
  }

  // ← AJOUT
  syncStatus(microserviceId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/jenkins/sync/${microserviceId}`, {});
  }

  getJenkinsLogs(jobName: string): Observable<any> {
  return this.http.get(`${this.apiUrl}/jenkins/logs/${jobName}/lastBuild`);
}

getAllRecentDeployments(): Observable<any[]> {
  return this.http.get<any[]>(`${this.apiUrl}/jenkins/deployments/recent`);
}

getLastBuildInfo(jobName: string): Observable<any> {
  return this.http.get(`${this.apiUrl}/jenkins/status/${jobName}`);
}
}