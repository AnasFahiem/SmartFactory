import { Component, OnInit, OnDestroy } from '@angular/core';
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
export class CameraControlComponent implements OnInit, OnDestroy {
    sources = [
        { label: 'Factory IP Webcam', value: 'http://192.168.1.50:8080/video' },
        { label: 'Local Webcam (Index 0)', value: '0' },
        { label: 'Custom RTSP Stream', value: 'custom' }
    ];

    selectedSource: any = 'http://192.168.1.50:8080/video';
    customIp: string = '';
    isRunning: boolean = false;
    message: string = '';

    constructor(public sensorService: SensorService) { }

    // Helper to get the stream directly from the service
    get liveStream(): string {
        return this.sensorService.currentFrame;
    }

    ngOnInit(): void {
        // Start SignalR connection when the component loads
        this.sensorService.start();
    }

    ngOnDestroy(): void {
        // Any specific cleanup if needed
    }

    toggleCamera() {
        const action = this.isRunning ? 'stop' : 'start';
        this.sensorService.toggleCamera(action).subscribe({
            next: (res) => {
                this.isRunning = !this.isRunning;
                this.message = `Camera ${this.isRunning ? 'started' : 'stopped'}.`;
            },
            error: (err) => {
                this.message = 'Error toggling camera. Check Azure logs.';
                console.error(err);
            }
        });
    }

    applyConfig() {
        const sourceToSend = this.selectedSource === 'custom' ? this.customIp : this.selectedSource;
        this.sensorService.setCameraSource(sourceToSend).subscribe({
            next: (res) => {
                this.message = 'Source configuration applied.';
            },
            error: (err) => {
                this.message = 'Failed to update source.';
            }
        });
    }
}