import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { SensorService } from '../services/sensor.service';
import { AuthService } from '../services/auth.service';

@Component({
    standalone: true,
    imports: [CommonModule, RouterModule],
    selector: 'app-sensor-dashboard',
    templateUrl: './sensor-dashboard.component.html',
    styleUrls: ['./sensor-dashboard.component.css']
})
export class SensorDashboardComponent implements OnInit {
    lastUpdate = new Date();

    constructor(public sensorService: SensorService, public authService: AuthService, private router: Router) {
        setInterval(() => {
            this.lastUpdate = new Date();
        }, 1000);
    }

    ngOnInit(): void {
        this.sensorService.start();
    }

    goToAnalytics(productNumber: string): void {
        this.router.navigate(['/analytics', productNumber]);
    }
}
