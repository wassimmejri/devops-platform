import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProjectService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ── Lister les projets ──────────────────────────
  getProjects(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/projects/`);
  }

  // ── Créer un projet ─────────────────────────────
  createProject(project: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/projects/`, project);
  }

  // ── Modifier un projet ──────────────────────────
  updateProject(id: number, project: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/projects/${id}`, project);
  }

  // ── Supprimer un projet ─────────────────────────
  deleteProject(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/${id}`);
  }
}