import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TerminalLogsComponent } from './terminal-logs.component';

describe('TerminalLogsComponent', () => {
  let component: TerminalLogsComponent;
  let fixture: ComponentFixture<TerminalLogsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TerminalLogsComponent]
    });
    fixture = TestBed.createComponent(TerminalLogsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
