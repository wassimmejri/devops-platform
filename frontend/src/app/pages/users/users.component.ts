import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../services/admin.service';
import { MessageService, ConfirmationService } from 'primeng/api';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.scss']
})
export class UsersComponent implements OnInit {

  users: any[] = [];
  loading = false;
  currentUserId: string = '';

  roleOptions = [
    { label: 'Admin DevOps', value: 'admin-devops' },
    { label: 'Developer',    value: 'developer' }
  ];

  constructor(
    private adminService: AdminService,
    private authService: AuthService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.currentUserId = user?.sub || user?.id || '';
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading = true;
    this.adminService.getUsers().subscribe({
      next: (data) => { this.users = data; this.loading = false; },
      error: () => {
        this.loading = false;
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les utilisateurs' });
      }
    });
  }

  changeRole(user: any, newRole: string): void {
    if (user.role === newRole) return;
    this.adminService.updateRole(user.keycloak_id, newRole).subscribe({
      next: () => {
        user.role = newRole;
        this.messageService.add({ severity: 'success', summary: 'Rôle mis à jour', detail: `${user.email} → ${newRole}` });
      },
      error: (err) => {
        this.messageService.add({ severity: 'error', summary: 'Erreur', detail: err?.error?.message || 'Impossible de changer le rôle' });
      }
    });
  }

  toggleStatus(user: any): void {
    const newStatus = !user.enabled;
    const action    = newStatus ? 'activer' : 'suspendre';
    this.confirmationService.confirm({
      message: `Voulez-vous ${action} <strong>${user.email}</strong> ?`,
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.adminService.updateStatus(user.keycloak_id, newStatus).subscribe({
          next: () => {
            user.enabled = newStatus;
            this.messageService.add({
              severity: newStatus ? 'success' : 'warn',
              summary: newStatus ? 'Utilisateur activé' : 'Utilisateur suspendu',
              detail: user.email
            });
          },
          error: () => { this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de modifier le statut' }); }
        });
      }
    });
  }

  deleteUser(user: any): void {
    this.confirmationService.confirm({
      message: `Supprimer définitivement <strong>${user.email}</strong> ? Cette action est irréversible.`,
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.adminService.deleteUser(user.keycloak_id).subscribe({
          next: () => {
            this.users = this.users.filter(u => u.keycloak_id !== user.keycloak_id);
            this.messageService.add({ severity: 'success', summary: 'Supprimé', detail: `${user.email} supprimé` });
          },
          error: () => { this.messageService.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de supprimer' }); }
        });
      }
    });
  }

  resetPassword(user: any): void {
    this.adminService.resetPassword(user.keycloak_id).subscribe({
      next: () => { this.messageService.add({ severity: 'success', summary: 'Email envoyé', detail: `Email de réinitialisation envoyé à ${user.email}` }); },
      error: () => { this.messageService.add({ severity: 'error', summary: 'Erreur', detail: "Impossible d'envoyer l'email" }); }
    });
  }

  isCurrentUser(user: any): boolean { return user.keycloak_id === this.currentUserId; }
  getRoleSeverity(role: string): string { return role === 'admin-devops' ? 'warning' : 'info'; }
  getStatusSeverity(enabled: boolean): string { return enabled ? 'success' : 'danger'; }

  getInitials(user: any): string {
    const name = `${user.first_name} ${user.last_name}`.trim() || user.email;
    const parts = name.split(' ').filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }

  getCreatedAt(timestamp: number): string {
    return new Date(timestamp).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }
}