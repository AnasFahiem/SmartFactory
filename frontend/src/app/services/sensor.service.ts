import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap, retry } from 'rxjs/operators';
import * as signalR from '@microsoft/signalr';

interface BackendStats {
    total_people: number;
    violations: number;
}

@Injectable({
    providedIn: 'root'
})
export class SensorService {
    // Python (camera/PPE) backend
    private cameraApiBase = 'http://localhost:5000';
    // .NET (MQTT/SignalR) backend
    private hubUrl = 'http://localhost:5005/hubs/factory';

    private hubConnection?: signalR.HubConnection;

    totalPeople: number = 0;
    violations: number = 0;

    // Keeping original properties for compatibility if needed, 
    // but focusing on the new ones for the factory monitor.
    temperature: number = 0;
    smoke: boolean = false;
    weight: number = 0;
    productNumber: string = '';

    connectionStatus: string = 'Disconnected';
    private hubStatus: string = 'Disconnected';
    private cameraStatus: string = 'Disconnected';

    constructor(private http: HttpClient) { }

    start(): void {
        this.startHubConnection();
        this.startCameraPolling();
    }

    private startHubConnection() {
        this.hubStatus = 'Connecting';
        this.updateStatusLabel();

        this.hubConnection = new signalR.HubConnectionBuilder()
            .withUrl(this.hubUrl)
            .withAutomaticReconnect()
            .build();

        this.hubConnection.on('ReceiveTemperatureUpdate', (temperature: number) => {
            this.temperature = temperature;
        });

        this.hubConnection.on('ReceiveSmokeUpdate', (smoke: boolean) => {
            this.smoke = smoke;
        });

        this.hubConnection.on('ReceiveWeightUpdate', (weight: number) => {
            this.weight = weight;
        });

        this.hubConnection.on('ReceiveProductNumberUpdate', (productNumber: string) => {
            this.productNumber = productNumber;
        });

        this.hubConnection.start()
            .then(() => {
                this.hubStatus = 'Connected';
                this.updateStatusLabel();
            })
            .catch(err => {
                console.error('SignalR connection error:', err);
                this.hubStatus = 'Error';
                this.updateStatusLabel();
            });

        this.hubConnection.onreconnecting(() => {
            this.hubStatus = 'Reconnecting';
            this.updateStatusLabel();
        });

        this.hubConnection.onreconnected(() => {
            this.hubStatus = 'Connected';
            this.updateStatusLabel();
        });

        this.hubConnection.onclose(() => {
            this.hubStatus = 'Disconnected';
            this.updateStatusLabel();
        });
    }

    private startCameraPolling() {
        this.cameraStatus = 'Polling';
        this.updateStatusLabel();

        interval(1000).pipe(
            switchMap(() => this.http.get<BackendStats>(`${this.cameraApiBase}/api/status`)),
            retry(3)
        ).subscribe({
            next: (stats) => {
                this.cameraStatus = 'Connected';
                this.updateStatusLabel();
                this.totalPeople = stats.total_people;
                this.violations = stats.violations;
            },
            error: (err) => {
                this.cameraStatus = 'Error';
                this.updateStatusLabel();
                console.error('Camera polling error:', err);
            }
        });
    }

    private updateStatusLabel() {
        this.connectionStatus = `Hub: ${this.hubStatus} | Camera API: ${this.cameraStatus}`;
    }

    setCameraSource(source: any): Observable<any> {
        return this.http.post(`${this.cameraApiBase}/api/camera/config`, { source });
    }

    toggleCamera(action: string): Observable<any> {
        return this.http.post(`${this.cameraApiBase}/api/camera/toggle`, { action });
    }
}
