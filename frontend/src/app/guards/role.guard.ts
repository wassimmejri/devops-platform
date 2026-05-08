import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {

  constructor(private auth: AuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    const requiredRoles: string[] = route.data['roles'] || [];
    const user = this.auth.getCurrentUser();
    const userRole = user?.role;

    // Si la route n’exige aucun rôle particulier, elle est accessible à tout le monde.
    if (requiredRoles.length === 0) return true;

    // Si l'utilisateur n'a pas le rôle requis, redirection vers le dashboard.
    if (!userRole || !requiredRoles.includes(userRole)) {
      this.router.navigate(['/dashboard']);
      return false;
    }
    return true;
  }
}