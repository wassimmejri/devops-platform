import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { tap } from 'rxjs/operators';


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
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token); // ← important
        localStorage.setItem('user', JSON.stringify(response.user));
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
      })
    );
  }

  // ── Register ────────────────────────────────────
  register(email: string, password: string, full_name: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/register`, {
      email,
      password,
      full_name
    });
  }

  // ── Logout ──────────────────────────────────────
  logout(): void {
    localStorage.removeItem('token');
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
    return !!localStorage.getItem('token');
  }

  // ── Get token ───────────────────────────────────
  getToken(): string | null {
    return localStorage.getItem('token');
  }
}