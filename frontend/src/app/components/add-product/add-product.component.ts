import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SensorService } from '../../services/sensor.service';

@Component({
  selector: 'app-add-product',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-product.component.html',
  styleUrls: ['./add-product.component.css']
})
export class AddProductComponent {
  product = {
    weight: null as number | null,
    code: ''
  };

  successMessage: string = '';
  errorMessage: string = '';

  constructor(private router: Router, private sensorService: SensorService) {}

  onSubmit() {
    this.successMessage = '';
    this.errorMessage = '';

    const code = this.product.code.trim();
    const weight = this.product.weight;
    if (!code) {
      this.errorMessage = 'Product code is required.';
      return;
    }

    if (weight === null || weight === undefined || Number.isNaN(Number(weight)) || Number(weight) < 0) {
      this.errorMessage = 'Weight must be zero or a positive number.';
      return;
    }

    this.sensorService.addProduct({
      productNumber: code,
      weight: Number(weight)
    }).subscribe({
      next: () => {
        this.successMessage = `Product code '${code}' added successfully!`;

        setTimeout(() => {
          this.product = { weight: null, code: '' };
          this.successMessage = '';
        }, 3000);
      },
      error: (err) => {
        console.error('Error adding product', err);
        this.errorMessage = err?.error?.message || 'Could not add product.';
      }
    });
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }
}
