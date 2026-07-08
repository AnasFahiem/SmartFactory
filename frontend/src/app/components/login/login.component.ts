import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
    standalone: true,
    imports: [CommonModule, FormsModule],
    selector: 'app-login',
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
    username = '';
    password = '';
    errorMessage = '';
    loading = false;
    returnUrl = '/dashboard';

    constructor(
        private authService: AuthService,
        private router: Router,
        private route: ActivatedRoute
    ) {}

    ngOnInit(): void {
        // If already logged in, redirect to dashboard
        if (this.authService.isLoggedIn()) {
            this.router.navigate(['/dashboard']);
            return;
        }

        // Get return url from route parameters or default to '/dashboard'
        this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
    }

    onSubmit(): void {
        if (!this.username.trim() || !this.password.trim()) {
            this.errorMessage = 'Please enter both username and password.';
            return;
        }

        this.loading = true;
        this.errorMessage = '';

        this.authService.login(this.username, this.password).subscribe({
            next: (res) => {
                this.loading = false;
                this.router.navigateByUrl(this.returnUrl);
            },
            error: (err) => {
                this.loading = false;
                this.errorMessage = err.error?.message || 'Login failed. Check your network or credentials.';
                console.error('Login error:', err);
            }
        });
    }
}
