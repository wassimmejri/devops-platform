import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AdminService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/admin/users`);
  }

  updateRole(keycloakId: string, role: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/admin/users/${keycloakId}/role`, { role });
  }

  updateStatus(keycloakId: string, enabled: boolean): Observable<any> {
    return this.http.put(`${this.apiUrl}/admin/users/${keycloakId}/status`, { enabled });
  }

  deleteUser(keycloakId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/admin/users/${keycloakId}`);
  }

  resetPassword(keycloakId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/users/${keycloakId}/reset-password`, {});
  }
}