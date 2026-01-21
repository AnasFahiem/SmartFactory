import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

// Suppress third-party library errors
const originalError = console.error;
console.error = function (...args: any[]) {
    if (args[0]?.message?.includes('checkout popup config')) {
        return;
    }
    originalError.apply(console, args);
};

platformBrowserDynamic()
    .bootstrapModule(AppModule)
    .catch(err => console.error(err));
