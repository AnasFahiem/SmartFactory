import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { SensorService } from '../../services/sensor.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-products-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './products-list.component.html',
  styleUrls: ['./products-list.component.css']
})
export class ProductsListComponent implements OnInit {
  products: any[] = [];
  loading: boolean = true;
  error: string = '';
  
  canEdit: boolean = false;
  editingProduct: any = null;

  constructor(
    private sensorService: SensorService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user && (user.role === 'Admin' || user.role === 'Manager')) {
      this.canEdit = true;
    }
    this.loadProducts();
  }

  loadProducts(): void {
    this.loading = true;
    this.sensorService.getAllProducts().subscribe({
      next: (data) => {
        this.products = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load products. ' + (err.error?.message || '');
        this.loading = false;
      }
    });
  }

  goToAnalytics(productNumber: string): void {
    this.router.navigate(['/analytics', productNumber]);
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  startEdit(product: any, event: Event): void {
    event.stopPropagation();
    this.editingProduct = { ...product };
  }

  cancelEdit(event: Event): void {
    event.stopPropagation();
    this.editingProduct = null;
  }

  saveEdit(event: Event): void {
    event.stopPropagation();
    if (!this.editingProduct) return;
    
    this.sensorService.updateProduct(this.editingProduct.id, this.editingProduct).subscribe({
      next: () => {
        this.editingProduct = null;
        this.loadProducts();
      },
      error: (err) => {
        alert('Failed to update product: ' + (err.error?.message || err.message));
      }
    });
  }

  deleteProduct(id: number, productNumber: string, event: Event): void {
    event.stopPropagation();
    if (confirm(`Are you sure you want to delete product ${productNumber}?`)) {
      this.sensorService.deleteProduct(id).subscribe({
        next: () => {
          this.loadProducts();
        },
        error: (err) => {
          alert('Failed to delete product: ' + (err.error?.message || err.message));
        }
      });
    }
  }
}
