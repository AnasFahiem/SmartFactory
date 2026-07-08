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
    weight: null,
    code: ''
  };

  successMessage: string = '';

  constructor(private router: Router, private sensorService: SensorService) {}

  onSubmit() {
    if (this.product.weight && this.product.code) {
      this.sensorService.addProduct({
        productNumber: this.product.code,
        weight: this.product.weight
      }).subscribe({
        next: (res) => {
          this.successMessage = `Product code '${this.product.code}' added successfully!`;
          
          setTimeout(() => {
            this.product = { weight: null as any, code: '' };
            this.successMessage = '';
          }, 3000);
        },
        error: (err) => {
          console.error('Error adding product', err);
        }
      });
    }
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }
}
