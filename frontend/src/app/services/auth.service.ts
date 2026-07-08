import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

interface LoginResponse {
  token: string;
  username: string;
  role: string;
  expiresAtUtc?: string;
}

interface CurrentUserResponse {
  username: string;
  role: string;
  expiresAtUtc?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  
  private currentUserSubject = new BehaviorSubject<LoginResponse | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    // If local storage has user info, load it
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
      try {
        const user = JSON.parse(savedUser) as LoginResponse;
        if (this.isExpired(user)) {
          this.clearSession(false);
        } else {
          this.currentUserSubject.next(user);
        }
      } catch (e) {
        localStorage.removeItem('currentUser');
      }
    }
  }

  isLoggedIn(): boolean {
    const user = this.currentUserSubject.value;
    if (!user) {
      return false;
    }

    if (this.isExpired(user)) {
      this.clearSession(false);
      return false;
    }

    return true;
  }

  getCurrentUser(): LoginResponse | null {
    return this.currentUserSubject.value;
  }

  hasAnyRole(roles: string[]): boolean {
    const user = this.getCurrentUser();
    return !!user && roles.includes(user.role);
  }

  getToken(): string | null {
    return this.currentUserSubject.value?.token || null;
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/api/auth/login`, { username, password })
      .pipe(
        tap(user => {
          this.storeUser(user);
        })
      );
  }

  refreshCurrentUser(): Observable<LoginResponse> {
    return this.http.get<CurrentUserResponse>(`${this.apiUrl}/api/auth/me`)
      .pipe(
        map(profile => {
          const current = this.currentUserSubject.value;
          if (!current?.token) {
            throw new Error('No active token.');
          }

          return {
            token: current.token,
            username: profile.username,
            role: profile.role,
            expiresAtUtc: profile.expiresAtUtc
          };
        }),
        tap(user => this.storeUser(user))
      );
  }

  register(user: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/api/auth/register`, user);
  }

  getAllUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/api/users`);
  }

  deleteUser(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/api/users/${id}`);
  }

  updateRole(id: number, role: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/api/users/${id}/role`, { role });
  }

  updateMyProfile(username?: string, password?: string): Observable<any> {
    const payload: any = {};
    if (username) payload.username = username;
    if (password) payload.password = password;
    return this.http.put(`${this.apiUrl}/api/auth/me`, payload);
  }

  clearSession(redirect: boolean = true): void {
    localStorage.removeItem('currentUser');
    this.currentUserSubject.next(null);
    if (redirect) {
      this.router.navigate(['/login']);
    }
  }

  logout(): void {
    const finishLogout = () => this.clearSession(true);

    if (!this.getToken()) {
      finishLogout();
      return;
    }

    this.http.post(`${this.apiUrl}/api/auth/logout`, {}).subscribe({
      next: finishLogout,
      error: finishLogout
    });
  }

  private storeUser(user: LoginResponse): void {
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.currentUserSubject.next(user);
  }

  private isExpired(user: LoginResponse): boolean {
    if (!user.expiresAtUtc) {
      return false;
    }

    const expiresAt = Date.parse(user.expiresAtUtc);
    return !Number.isNaN(expiresAt) && expiresAt <= Date.now();
  }
}
