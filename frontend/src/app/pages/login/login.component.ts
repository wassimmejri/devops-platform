import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {

  email: string = '';
  password: string = '';
  loading: boolean = false;
  rememberMe: boolean = false;
  submitted: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    // Si déjà authentifié, redirection sans message
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
    }
  }

  login(): void {
    this.submitted = true;

    // Validation des champs
    if (!this.email || !this.password) {
      this.messageService.add({
        severity: 'warn',
        summary: '⚠️ Authentification incomplète',
        detail: 'Veuillez saisir votre email et votre mot de passe.',
        life: 4000
      });
      return;
    }

    this.loading = true;

    this.authService.login(this.email, this.password).subscribe({
      next: () => {
        if (this.rememberMe) {
          localStorage.setItem('devboard_remember', this.email);
        }

        // Toast de succès avec message dynamique
        const hour = new Date().getHours();
        const greeting = hour < 12 ? 'Bonjour' : (hour < 18 ? 'Bon après-midi' : 'Bonsoir');
        
        this.messageService.add({
          severity: 'success',
          summary: `✅ ${greeting}, ${this.getUserDisplayName()} !`,
          detail: 'Authentification réussie. Redirection vers le dashboard...',
          life: 2500
        });

        // Redirection après un court délai pour laisser le temps de lire le toast
        setTimeout(() => {
          this.router.navigate(['/dashboard']);
        }, 1500);
      },
      error: (err) => {
        this.loading = false;
        
        // Message d'erreur contextualisé
        let errorDetail = 'Email ou mot de passe incorrect.';
        if (err.status === 401) {
          errorDetail = 'Identifiants invalides. Vérifiez votre email et mot de passe.';
        } else if (err.status === 502 || err.status === 503) {
          errorDetail = 'Le service d\'authentification est momentanément indisponible. Veuillez réessayer.';
        } else if (err.status === 0) {
          errorDetail = 'Impossible de contacter le serveur. Vérifiez votre connexion réseau.';
        }

        this.messageService.add({
          severity: 'error',
          summary: '❌ Échec de l\'authentification',
          detail: errorDetail,
          life: 6000,
          sticky: false
        });
      }
    });
  }

  private getUserDisplayName(): string {
    // Tenter de récupérer le nom depuis le localStorage ou utiliser l'email
    const user = this.authService.getCurrentUser();
    if (user?.full_name) {
      return user.full_name.split(' ')[0]; // Premier prénom
    }
    return this.email.split('@')[0]; // Partie locale de l'email
  }
}