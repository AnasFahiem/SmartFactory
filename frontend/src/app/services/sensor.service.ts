import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap, retry } from 'rxjs/operators';

interface BackendStats {
    total_people: number;
    violations: number;
}

@Injectable({
    providedIn: 'root'
})
export class SensorService {
    private apiUrl = 'http://localhost:5000/api/status';

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
        this.connectionStatus = 'Polling';

        // Poll every 1 second
        interval(1000).pipe(
            switchMap(() => this.http.get<BackendStats>(this.apiUrl)),
            retry(3) // Retry failed requests
        ).subscribe({
            next: (stats) => {
                this.connectionStatus = 'Connected';
                this.totalPeople = stats.total_people;
                this.violations = stats.violations;

                // Map to existing dummy fields for visualization if desired
                // or just leave them as defaults.
                this.smoke = this.violations > 0; // Turn on smoke alarm if violations exist?
            },
            error: (err) => {
                this.connectionStatus = 'Error';
                console.error('Polling error:', err);
            }
        });
    }
    setCameraSource(source: any): Observable<any> {
        return this.http.post('http://localhost:5000/api/camera/config', { source });
    }

    toggleCamera(action: string): Observable<any> {
        return this.http.post('http://localhost:5000/api/camera/toggle', { action });
    }
}
