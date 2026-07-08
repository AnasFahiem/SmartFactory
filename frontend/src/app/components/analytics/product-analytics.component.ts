import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { SensorService } from '../../services/sensor.service';

@Component({
  selector: 'app-product-analytics',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './product-analytics.component.html',
  styleUrls: ['./product-analytics.component.css']
})
export class ProductAnalyticsComponent implements OnInit {
  productNumber: string = '';
  analyticsData: any = null;
  loading: boolean = true;
  error: string = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private sensorService: SensorService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const pNum = params.get('productNumber');
      if (pNum) {
        this.productNumber = pNum;
        this.loadAnalytics();
      } else {
        this.error = 'No product number specified.';
        this.loading = false;
      }
    });
  }

  loadAnalytics(): void {
    this.loading = true;
    this.error = '';
    this.sensorService.getProductAnalytics(this.productNumber).subscribe({
      next: (data) => {
        this.analyticsData = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to load analytics for this product.';
        this.loading = false;
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  isVarianceGood(): boolean {
    if (!this.analyticsData || this.analyticsData.totalScans === 0 || this.analyticsData.idealWeight === null) {
      return true;
    }
    const tenPercent = this.analyticsData.idealWeight * 0.10;
    return Math.abs(this.analyticsData.variance) <= tenPercent;
  }
}
