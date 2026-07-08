import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  currentUsername: string = '';
  newUsername: string = '';
  newPassword: string = '';
  confirmPassword: string = '';
  
  successMessage: string = '';
  errorMessage: string = '';
  isSubmitting: boolean = false;

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      this.currentUsername = user.username;
      this.newUsername = user.username;
    }
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  onSubmit(): void {
    this.successMessage = '';
    this.errorMessage = '';

    if (this.newPassword && this.newPassword !== this.confirmPassword) {
      this.errorMessage = 'Passwords do not match.';
      return;
    }

    const updatedUsername = this.newUsername !== this.currentUsername ? this.newUsername : undefined;
    const updatedPassword = this.newPassword ? this.newPassword : undefined;

    if (!updatedUsername && !updatedPassword) {
      this.errorMessage = 'No changes made.';
      return;
    }

    this.isSubmitting = true;
    this.authService.updateMyProfile(updatedUsername, updatedPassword).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        if (res.requireRelogin) {
          this.authService.logout();
          this.router.navigate(['/login']);
        } else {
          this.successMessage = 'Profile updated successfully!';
          this.newPassword = '';
          this.confirmPassword = '';
        }
      },
      error: (err) => {
        this.isSubmitting = false;
        this.errorMessage = err.error?.message || 'Failed to update profile.';
      }
    });
  }
}
