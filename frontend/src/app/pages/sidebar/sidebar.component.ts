import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ConfirmationService } from 'primeng/api';

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
export class SidebarComponent implements OnInit {

  collapsed: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    const saved = localStorage.getItem('devboard_sidebar_collapsed');
    if (saved !== null) {
      this.collapsed = saved === 'true';
    }
  }

  toggleCollapse(): void {
    this.collapsed = !this.collapsed;
    localStorage.setItem('devboard_sidebar_collapsed', String(this.collapsed));
  }

  get userName(): string {
    const user = this.authService.getCurrentUser();
    return user?.full_name || user?.name || user?.email || 'Utilisateur';
  }

  get userInitials(): string {
    const name = this.userName;
    const parts = name.split(' ').filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  confirmLogout(event: Event): void {
    this.confirmationService.confirm({
      target: event.target as EventTarget,
      message: 'Voulez-vous vraiment vous déconnecter ?',
      icon: 'pi pi-sign-out',
      key: 'sidebar-logout',
      accept: () => this.authService.logout()
    });
  }
}