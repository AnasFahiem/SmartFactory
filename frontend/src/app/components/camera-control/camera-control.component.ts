import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SensorService } from '../../services/sensor.service';

@Component({
    standalone: true,
    imports: [CommonModule, FormsModule],
    selector: 'app-camera-control',
    templateUrl: './camera-control.component.html',
    styleUrls: ['./camera-control.component.css']
})
export class CameraControlComponent implements OnInit {

    sources = [
        { label: 'Local Webcam (Index 0)', value: 0 },
        { label: 'Local Webcam (Index 1)', value: 1 },
        { label: 'ESP32 / IP Camera (Custom URL)', value: 'custom' }
    ];

    selectedSource: any = 0;
    customIp: string = 'http://192.168.1.100:81/stream';
    isRunning: boolean = true;
    message: string = '';

    constructor(private sensorService: SensorService) { }

    ngOnInit(): void {
        // Ideally fetch status from backend on init
        this.checkStatus();
    }

    checkStatus() {
        // We'll add this method to service later
        // For now assume default
    }

    toggleCamera() {
        const action = this.isRunning ? 'stop' : 'start';
        this.sensorService.toggleCamera(action).subscribe(res => {
            this.isRunning = res.is_running;
            this.message = res.message;
        });
    }

    applyConfig() {
        let sourceToSend = this.selectedSource;
        if (this.selectedSource === 'custom') {
            sourceToSend = this.customIp;
        }

        this.sensorService.setCameraSource(sourceToSend).subscribe(res => {
            this.message = res.message;
            // Restart stream if it was running to apply changes effectively
            if (this.isRunning) {
                // Optionally force reload image or just let backend handle it
            }
        });
    }
}
