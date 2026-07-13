import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { FormsModule } from '@angular/forms'; // For ngModel

import { AppComponent } from './app.component';
import { SensorDashboardComponent } from './components/sensor-dashboard.component';
import { CameraControlComponent } from './components/camera-control/camera-control.component';
import { LoginComponent } from './components/login/login.component';
import { AddProductComponent } from './components/add-product/add-product.component';
import { AddUserComponent } from './components/add-user/add-user.component';
import { ProductAnalyticsComponent } from './components/analytics/product-analytics.component';
import { ProductsListComponent } from './components/products-list/products-list.component';
import { ProfileComponent } from './components/profile/profile.component';
import { SensorService } from './services/sensor.service';
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { authGuard } from './guards/auth.guard';

const routes: Routes = [
    { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
    { path: 'login', component: LoginComponent },
    { path: 'dashboard', component: SensorDashboardComponent, canActivate: [authGuard] },
    { path: 'stream', component: CameraControlComponent, canActivate: [authGuard], data: { roles: ['Manager', 'Admin'] } },
    { path: 'add-product', component: AddProductComponent, canActivate: [authGuard], data: { roles: ['Manager', 'Admin'] } },
    { path: 'add-user', component: AddUserComponent, canActivate: [authGuard], data: { roles: ['Admin'] } },
    { path: 'analytics/:productNumber', component: ProductAnalyticsComponent, canActivate: [authGuard] },
    { path: 'products-list', component: ProductsListComponent, canActivate: [authGuard] },
    { path: 'profile', component: ProfileComponent, canActivate: [authGuard] }
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
        LoginComponent,
        AddProductComponent,
        AddUserComponent,
        ProductAnalyticsComponent,
        ProductsListComponent,
        ProfileComponent,
        HttpClientModule,
        FormsModule,
        RouterModule.forRoot(routes)
    ],
    providers: [
        SensorService,
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
    ],
    bootstrap: [AppComponent]
})
export class AppModule { }
