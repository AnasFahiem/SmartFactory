import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import * as signalR from '@microsoft/signalr';

interface BackendStats {
    total_people: number;
    violations: number;
}

@Injectable({
    providedIn: 'root'
})
export class SensorService {
    private apiUrl = 'https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net';
    private hubUrl = 'https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net/hubs/factory';
    private hubConnection: signalR.HubConnection | null = null;

    // --- Data Properties ---
    public totalPeople: number = 0;
    public violations: number = 0;
    public temperature: number = 0;
    public smoke: boolean = false;
    public weight: number = 0;
    public productNumber: string = '';
    public currentFrame: string = ''; 
    public connectionStatus: string = 'Disconnected';
    public aiAlertMessage: string = '';

    constructor(private http: HttpClient) { }

    start(): void {
        this.startHubConnection();
        // Old Polling removed to fix "ti" timeout errors.
    }

    private startHubConnection(): void {
        this.connectionStatus = 'Connecting';
        this.hubConnection = new signalR.HubConnectionBuilder()
            .withUrl(this.hubUrl)
            .withAutomaticReconnect()
            .build();

        // --- SignalR Listeners ---

        // NEW: Stats Listener (Replaces the polling)
        this.hubConnection.on('ReceiveStatsUpdate', (stats: BackendStats) => {
            this.totalPeople = stats.total_people;
            this.violations = stats.violations;
        });

        // Camera feed listener
        this.hubConnection.on('ReceiveCameraFrame', (base64Data: string) => {
            this.currentFrame = base64Data.startsWith('data:image') 
                ? base64Data 
                : `data:image/jpeg;base64,${base64Data}`;
        });

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

        this.hubConnection.on('ReceiveAiAlert', (message: string) => {
            this.aiAlertMessage = message;
            // Auto clear alert after 10 seconds
            setTimeout(() => {
                this.aiAlertMessage = '';
            }, 10000);
        });

        // --- Connection Management ---
        this.hubConnection.start()
            .then(() => {
                this.connectionStatus = 'Connected';
                console.log('SignalR Connected to Azure.');
            })
            .catch(err => {
                this.connectionStatus = 'Error';
                console.error('SignalR connection error:', err);
            });

        this.hubConnection.onreconnecting(() => this.connectionStatus = 'Reconnecting');
        this.hubConnection.onreconnected(() => this.connectionStatus = 'Connected');
        this.hubConnection.onclose(() => this.connectionStatus = 'Disconnected');
    }

    setCameraSource(source: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/api/camera/config`, { source });
    }

    toggleCamera(action: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/api/camera/toggle`, { action });
    }

    addProduct(product: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/api/products`, product);
    }

    getProductAnalytics(productNumber: string): Observable<any> {
        return this.http.get(`${this.apiUrl}/api/products/analytics/${productNumber}`);
    }

    resetProductScans(productNumber: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/api/products/analytics/${encodeURIComponent(productNumber)}/scans`);
    }

    getAllProducts(): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/api/products`);
    }

    updateProduct(id: number, product: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/api/products/${id}`, product);
    }

    deleteProduct(id: number): Observable<any> {
        return this.http.delete(`${this.apiUrl}/api/products/${id}`);
    }
}