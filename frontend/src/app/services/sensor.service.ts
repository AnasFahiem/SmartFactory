
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
    private apiUrl = 'http://localhost:5000/api/status';
    private hubUrl = 'http://localhost:5005/hubs/factory';
    private hubConnection: signalR.HubConnection | null = null;

    totalPeople: number = 0;
    violations: number = 0;

    // Keeping original properties for compatibility if needed, 
    // but focusing on the new ones for the factory monitor.
    temperature: number = 0;
    smoke: boolean = false;
    weight: number = 0;
    productNumber: string = '';

    connectionStatus: string = 'Disconnected';

    constructor(private http: HttpClient) { }

    start(): void {
        this.startHubConnection();
        // Optionally keep polling Flask backend for totalPeople/violations
        interval(1000).pipe(
            switchMap(() => this.http.get<BackendStats>(this.apiUrl)),
            retry(3)
        ).subscribe({
            next: (stats) => {
                this.totalPeople = stats.total_people;
                this.violations = stats.violations;
            },
            error: (err) => {
                // Only log error, don't set connectionStatus here
                console.error('Polling error:', err);
            }
        });
    }

    private startHubConnection(): void {
        this.connectionStatus = 'Connecting';
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
                this.connectionStatus = 'Connected';
            })
            .catch(err => {
                this.connectionStatus = 'Error';
                console.error('SignalR connection error:', err);
            });

        this.hubConnection.onreconnecting(() => {
            this.connectionStatus = 'Reconnecting';
        });
        this.hubConnection.onreconnected(() => {
            this.connectionStatus = 'Connected';
        });
        this.hubConnection.onclose(() => {
            this.connectionStatus = 'Disconnected';
        });
    }
    setCameraSource(source: any): Observable<any> {
        return this.http.post('http://localhost:5000/api/camera/config', { source });
    }

    toggleCamera(action: string): Observable<any> {
        return this.http.post('http://localhost:5000/api/camera/toggle', { action });
    }
}
