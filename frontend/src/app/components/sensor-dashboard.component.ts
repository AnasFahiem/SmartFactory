import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SensorService } from '../services/sensor.service';

@Component({
    standalone: true,
    imports: [CommonModule],
    selector: 'app-sensor-dashboard',
    templateUrl: './sensor-dashboard.component.html',
    styleUrls: ['./sensor-dashboard.component.css']
})
export class SensorDashboardComponent implements OnInit {
    lastUpdate = new Date();

    constructor(public sensorService: SensorService) {
        setInterval(() => {
            this.lastUpdate = new Date();
        }, 1000);
    }

    ngOnInit(): void {
        this.sensorService.start();
    }
}
