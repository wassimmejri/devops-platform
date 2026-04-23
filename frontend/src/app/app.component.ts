import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter, Subscription } from 'rxjs';

// Routes qui n'affichent PAS la sidebar
const NO_SIDEBAR_ROUTES = ['/login'];

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {

  title = 'frontend';
  showSidebar = false;
  sidebarCollapsed = false;

  private routerSub!: Subscription;
  private storageSub!: () => void;

  constructor(private router: Router) {}

  ngOnInit(): void {
    // Sync état collapsed avec localStorage (mis à jour par SidebarComponent)
    this.syncCollapsed();

    // Écoute les changements de route
    this.routerSub = this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        this.showSidebar = !NO_SIDEBAR_ROUTES.some(r => e.urlAfterRedirects.startsWith(r));
        this.syncCollapsed();
      });

    // Écoute les changements de localStorage (toggle sidebar)
    const handler = () => this.syncCollapsed();
    window.addEventListener('storage', handler);
    this.storageSub = () => window.removeEventListener('storage', handler);

    // Polling léger pour détecter le toggle dans le même onglet
    setInterval(() => this.syncCollapsed(), 300);
  }

  ngOnDestroy(): void {
    if (this.routerSub) this.routerSub.unsubscribe();
    if (this.storageSub) this.storageSub();
  }

  private syncCollapsed(): void {
    const saved = localStorage.getItem('devboard_sidebar_collapsed');
    this.sidebarCollapsed = saved === 'true';
  }
}