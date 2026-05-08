import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, throwError } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private apiUrl = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  // ── Login ───────────────────────────────────────
  login(email: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/login`, { email, password }).pipe(
      tap((response: any) => {
        localStorage.setItem('access_token', response.access_token);         // ← corrigé
        localStorage.setItem('refresh_token', response.refresh_token);
        localStorage.setItem('user', JSON.stringify(response.user));        // user contient "role"
      })
    );
  }

  // ── Refresh token ───────────────────────────────
refreshToken(): Observable<any> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    return throwError(() => new Error('No refresh token available'));
  }
  return this.http.post(`${this.apiUrl}/auth/refresh`, { refresh_token: refreshToken }).pipe(
    tap((response: any) => {
      localStorage.setItem('access_token', response.access_token);
      if (response.refresh_token) {
        localStorage.setItem('refresh_token', response.refresh_token);
      }
      // ← AJOUT : mettre à jour le user avec le bon rôle
      if (response.user) {
        localStorage.setItem('user', JSON.stringify(response.user));
      }
    })
  );
}

  // ── Register ────────────────────────────────────
  register(email: string, password: string, full_name: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/register`, { email, password, full_name });
  }

  // ── Logout ──────────────────────────────────────
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.router.navigate(['/login']);
  }

  // ── Get current user ────────────────────────────
  getCurrentUser(): any {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  // ── Is logged in ────────────────────────────────
  isLoggedIn(): boolean {
    return !!localStorage.getItem('access_token');
  }

  // ── Get token ───────────────────────────────────
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  // ── Role helpers ────────────────────────────────
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.role === 'admin-devops';
  }

  getRole(): string | null {
    const user = this.getCurrentUser();
    return user?.role || null;
  }
}