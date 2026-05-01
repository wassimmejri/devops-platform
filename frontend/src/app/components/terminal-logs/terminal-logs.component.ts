import { 
  Component, Input, OnInit, OnDestroy, 
  ViewChild, ElementRef, AfterViewChecked 
} from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-terminal-logs',
  templateUrl: './terminal-logs.component.html',
  styleUrls: ['./terminal-logs.component.scss']
})
export class TerminalLogsComponent implements OnInit, OnDestroy, AfterViewChecked {

  @Input() jobName!: string;
  @Input() buildNumber!: number;
  @ViewChild('terminalBody') terminalBody!: ElementRef;

  lines: string[]   = [];
  isRunning         = true;
  result            = '';
  private sub!: Subscription;
  private shouldScroll = false;

  constructor(private socketService: SocketService) {}

  ngOnInit(): void {
    this.lines = ['Connexion au pipeline Jenkins...', ''];

    this.sub = this.socketService
      .streamJenkinsBuildLogs(this.jobName, this.buildNumber)
      .subscribe({
        next: (data: any) => {
          if (data.type === 'line') {
            this.lines.push(data.line);
            this.shouldScroll = true;
          } else if (data.type === 'finished') {
            this.isRunning = false;
            this.result    = data.result;
            this.lines.push('');
            this.lines.push(
              data.result === 'SUCCESS'
                ? '✅ Pipeline terminé avec succès !'
                : '❌ Pipeline terminé avec des erreurs.'
            );
            this.shouldScroll = true;
          }
        },
        error: () => {
          this.isRunning = false;
          this.lines.push('❌ Erreur de connexion au stream de logs.');
        }
      });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.socketService.disconnect('/jenkins-logs');
  }

  isErrorLine(line: string): boolean {
    const lower = line.toLowerCase();
    return lower.includes('error') ||
           lower.includes('failed') ||
           lower.includes('exception');
  }

  isSuccessLine(line: string): boolean {
    const lower = line.toLowerCase();
    return lower.includes('success') ||
           lower.includes('reussi') ||
           lower.includes('completed');
  }

  isWarningLine(line: string): boolean {
    const lower = line.toLowerCase();
    return lower.includes('warn') ||
           lower.includes('warning');
  }

  private scrollToBottom(): void {
    try {
      const el = this.terminalBody.nativeElement;
      el.scrollTop = el.scrollHeight;
    } catch {}
  }
}