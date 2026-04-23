import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';

@Injectable({ providedIn: 'root' })
export class ToastService {
  constructor(private messageService: MessageService) {}

  success(summary: string, detail?: string): void {
    this.messageService.add({
      severity: 'success',
      summary,
      detail,
      life: 4000
    });
  }

  info(summary: string, detail?: string): void {
    this.messageService.add({
      severity: 'info',
      summary,
      detail,
      life: 4000
    });
  }

  warn(summary: string, detail?: string): void {
    this.messageService.add({
      severity: 'warn',
      summary,
      detail,
      life: 5000
    });
  }

  error(summary: string, detail?: string): void {
    this.messageService.add({
      severity: 'error',
      summary,
      detail,
      life: 6000,
      sticky: false
    });
  }

  // Toast spécifiques DevOps
  deploymentStarted(microserviceName: string): void {
    this.info('🚀 Déploiement initié', `${microserviceName} - Pipeline Jenkins en cours...`);
  }

  deploymentSuccess(microserviceName: string, version?: string): void {
    this.success('✅ Déploiement réussi', `${microserviceName} ${version ? 'v' + version : ''} est en ligne`);
  }

  deploymentFailed(microserviceName: string, reason?: string): void {
    this.error('❌ Échec du déploiement', `${microserviceName} - ${reason || 'Consultez les logs Jenkins'}`);
  }

  projectCreated(projectName: string, namespace: string): void {
    this.success('📁 Projet créé', `${projectName} · Namespace ${namespace} provisionné`);
  }

  projectDeleted(projectName: string): void {
    this.info('🗑️ Projet supprimé', `${projectName} et ses ressources ont été nettoyés`);
  }

  microserviceAdded(name: string): void {
    this.success('➕ Microservice ajouté', `${name} est prêt à être déployé`);
  }

  podRestarted(podName: string): void {
    this.success('🔄 Pod redémarré', `${podName} a été recréé avec succès`);
  }

  logsCopied(): void {
    this.info('📋 Logs copiés', 'Les logs ont été copiés dans le presse-papier');
  }

  clusterHealthy(): void {
    this.success('🟢 Cluster opérationnel', 'Tous les nœuds sont en état Ready');
  }

  clusterDegraded(failedNodes: number): void {
    this.warn('🟡 Cluster dégradé', `${failedNodes} nœud(s) en état NotReady`);
  }

  autoRefreshToggled(enabled: boolean): void {
    this.info(enabled ? '🔄 Auto‑refresh activé' : '⏸️ Auto‑refresh désactivé', 
               enabled ? `Rafraîchissement toutes les 30s` : '');
  }
}