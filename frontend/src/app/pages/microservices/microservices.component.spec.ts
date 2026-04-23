import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MicroservicesComponent } from './microservices.component';

describe('MicroservicesComponent', () => {
  let component: MicroservicesComponent;
  let fixture: ComponentFixture<MicroservicesComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MicroservicesComponent]
    });
    fixture = TestBed.createComponent(MicroservicesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
