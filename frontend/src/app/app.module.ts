import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { FormsModule } from '@angular/forms'; // For ngModel

import { AppComponent } from './app.component';
import { SensorDashboardComponent } from './components/sensor-dashboard.component';
import { CameraControlComponent } from './components/camera-control/camera-control.component';
import { SensorService } from './services/sensor.service';

const routes: Routes = [
    { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
    { path: 'dashboard', component: SensorDashboardComponent },
    { path: 'stream', component: CameraControlComponent }
];

@NgModule({
    declarations: [
        AppComponent
    ],
    imports: [
        BrowserModule,
        CommonModule,
        SensorDashboardComponent,
        CameraControlComponent,
        HttpClientModule,
        FormsModule,
        RouterModule.forRoot(routes)
    ],
    providers: [SensorService],
    bootstrap: [AppComponent]
})
export class AppModule { }
