import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'adminFilter' })
export class AdminFilterPipe implements PipeTransform {
  transform(users: any[], filter: string): number {
    if (!users) return 0;
    switch (filter) {
      case 'admin-devops': return users.filter(u => u.role === 'admin-devops').length;
      case 'developer':    return users.filter(u => u.role === 'developer').length;
      case 'suspended':    return users.filter(u => !u.enabled).length;
      default:             return 0;
    }
  }
}