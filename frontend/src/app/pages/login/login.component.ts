import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit, OnDestroy {

  email: string = '';
  password: string = '';
  loading: boolean = false;
  redirecting: boolean = false;   // ← nouvel état
  rememberMe: boolean = false;
  submitted: boolean = false;
  showPassword: boolean = false;

  // ── Typewriter ───────────────────────────────────
  terminalText: string = '';
  private fullTerminalText: string = 'v1.0 · PFE 2026 · DevOps Platform';
  private typewriterInterval: any;
  private typewriterStarted: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private messageService: MessageService
  ) {}

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
      return;
    }

    // Pré-remplir l'email si "remember me" avait été coché
    const savedEmail = localStorage.getItem('devboard_remember');
    if (savedEmail) {
      this.email = savedEmail;
      this.rememberMe = true;
    }

    setTimeout(() => this.startTypewriter(), 500);
  }

  ngOnDestroy(): void {
    if (this.typewriterInterval) {
      clearInterval(this.typewriterInterval);
    }
  }

  startTypewriter(): void {
    if (this.typewriterStarted) return;
    this.typewriterStarted = true;

    let i = 0;
    this.terminalText = '';
    if (this.typewriterInterval) clearInterval(this.typewriterInterval);
    this.typewriterInterval = setInterval(() => {
      if (i < this.fullTerminalText.length) {
        this.terminalText += this.fullTerminalText.charAt(i);
        i++;
      } else {
        clearInterval(this.typewriterInterval);
        this.terminalText = this.fullTerminalText;
      }
    }, 80);
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  login(): void {
    this.submitted = true;

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
        } else {
          localStorage.removeItem('devboard_remember');
        }

        const hour = new Date().getHours();
        const greeting = hour < 12 ? 'Bonjour' : (hour < 18 ? 'Bon après-midi' : 'Bonsoir');
        const user = this.authService.getCurrentUser();
        const role = user?.role === 'admin-devops' ? ' (Administrateur)' : ' (Développeur)';

        this.messageService.add({
          severity: 'success',
          summary: `✅ ${greeting}, ${this.getUserDisplayName()}${role} !`,
          detail: 'Authentification réussie. Redirection vers le dashboard...',
          life: 2500
        });

        // ── Passer en mode "redirecting" pour animer le logo ──
        this.loading = false;
        this.redirecting = true;

        // Typewriter passe en mode "connecting..."
        if (this.typewriterInterval) clearInterval(this.typewriterInterval);
        this.terminalText = 'Connexion établie · Chargement du dashboard...';

        setTimeout(() => {
          this.router.navigate(['/dashboard']);
        }, 1500);
      },
      error: (err) => {
        this.loading = false;
        this.redirecting = false;

        let errorDetail = 'Email ou mot de passe incorrect.';
        if (err.status === 401) {
          errorDetail = 'Identifiants invalides. Vérifiez votre email et mot de passe.';
        } else if (err.status === 429) {
          errorDetail = 'Trop de tentatives. Veuillez patienter avant de réessayer.';
        } else if (err.status === 403) {
          errorDetail = 'Compte bloqué ou accès refusé. Contactez votre administrateur.';
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
    const user = this.authService.getCurrentUser();
    if (user?.full_name) {
      return user.full_name.split(' ')[0];
    }
    return this.email.split('@')[0];
  }
}