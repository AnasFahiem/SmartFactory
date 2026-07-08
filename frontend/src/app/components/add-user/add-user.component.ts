import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-add-user',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-user.component.html',
  styleUrls: ['./add-user.component.css']
})
export class AddUserComponent implements OnInit {
  users: any[] = [];
  
  newUser = {
    username: '',
    email: '',
    password: '',
    role: 'User'
  };

  successMessage: string = '';
  errorMessage: string = '';

  constructor(private router: Router, private authService: AuthService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.authService.getAllUsers().subscribe({
      next: (data) => {
        this.users = data;
      },
      error: (err) => {
        console.error('Failed to load users', err);
      }
    });
  }

  onSubmit() {
    if (this.newUser.username && this.newUser.password && this.newUser.role) {
      this.errorMessage = '';
      this.authService.register(this.newUser).subscribe({
        next: (res) => {
          this.successMessage = `User '${this.newUser.username}' added successfully as ${this.newUser.role}!`;
          this.loadUsers(); // refresh table
          
          setTimeout(() => {
            this.newUser = { username: '', email: '', password: '', role: 'User' };
            this.successMessage = '';
          }, 3000);
        },
        error: (err) => {
          console.error('Error adding user', err);
          this.errorMessage = err.error?.message || 'Failed to create user. Please try again.';
        }
      });
    }
  }

  deleteUser(id: number, username: string) {
    if (confirm(`Are you sure you want to delete user '${username}'?`)) {
      this.authService.deleteUser(id).subscribe({
        next: () => {
          this.loadUsers();
        },
        error: (err) => {
          alert(err.error?.message || 'Failed to delete user');
        }
      });
    }
  }

  updateRole(id: number, role: string) {
    this.authService.updateRole(id, role).subscribe({
      next: () => {
        this.loadUsers();
      },
      error: (err) => {
        alert(err.error?.message || 'Failed to update role');
        this.loadUsers(); // reload to revert change in UI
      }
    });
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }
}
