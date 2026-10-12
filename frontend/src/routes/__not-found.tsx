import { Link } from '@tanstack/react-router';
import { Home, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-canvas px-4">
      <div className="text-center max-w-md">
        <div className="mb-8">
          <span className="text-9xl font-bold text-brand-primary/10">404</span>
        </div>
        <h1 className="text-headline-xl text-text-primary mb-4">Page Not Found</h1>
        <p className="text-text-secondary text-body-lg mb-8">
          Sorry, we couldn't find the page you're looking for. It might have been moved or doesn't
          exist.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/today"
            className={cn(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors',
              'bg-brand-primary text-brand-on-primary hover:bg-brand-primary-hover'
            )}
          >
            <Home className="w-4 h-4" />
            Go to Dashboard
          </Link>
          <Link
            to="/appointments"
            className={cn(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors',
              'border border-border-default text-text-secondary hover:bg-bg-elevated'
            )}
          >
            <Search className="w-4 h-4" />
            Browse Appointments
          </Link>
        </div>
      </div>
    </div>
  );
}
