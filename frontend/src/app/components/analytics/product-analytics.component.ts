import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { SensorService } from '../../services/sensor.service';
import { AuthService } from '../../services/auth.service';

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
  resetMessage: string = '';
  resetLoading: boolean = false;
  canResetScans: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private sensorService: SensorService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.canResetScans = this.authService.hasAnyRole(['Manager', 'Admin']);
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

  resetScans(): void {
    if (!this.canResetScans || this.resetLoading) {
      return;
    }

    const confirmed = window.confirm(`Reset all scans for product ${this.productNumber}?`);
    if (!confirmed) {
      return;
    }

    this.resetLoading = true;
    this.error = '';
    this.resetMessage = '';

    this.sensorService.resetProductScans(this.productNumber).subscribe({
      next: (result) => {
        this.resetMessage = `Reset complete. Deleted ${result.deletedCount || 0} scans.`;
        this.resetLoading = false;
        this.loadAnalytics();
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to reset scans for this product.';
        this.resetLoading = false;
      }
    });
  }

  isScanGood(scan: any): boolean {
    return scan?.isWithinTolerance !== false;
  }
}
