import { Link } from '@tanstack/react-router';
import { AlertTriangle, Bug, Home, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ErrorPage() {
  // In manual routing, we don't have useRouteError - we'll show a generic error
  const isErrorBoundary = true;

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-canvas px-4">
      <div className="text-center max-w-md">
        <div className="mb-8">
          <div
            className={cn(
              'w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4',
              isErrorBoundary ? 'bg-status-error/10' : 'bg-status-warning/10'
            )}
          >
            {isErrorBoundary ? (
              <Bug className="w-10 h-10 text-status-error" />
            ) : (
              <AlertTriangle className="w-10 h-10 text-status-warning" />
            )}
          </div>
        </div>
        <h1 className="text-headline-xl text-text-primary mb-4">
          {isErrorBoundary ? 'Something went wrong' : 'Page Error'}
        </h1>
        <p className="text-text-secondary text-body-lg mb-8">
          {isErrorBoundary
            ? 'An unexpected error occurred. Our team has been notified.'
            : 'There was an error loading this page. Please try again.'}
        </p>

        {isErrorBoundary && import.meta.env.DEV && (
          <details className="mb-8 text-left p-4 bg-bg-elevated rounded-lg border border-border-subtle">
            <summary className="cursor-pointer font-medium text-text-primary mb-2">
              Error Details
            </summary>
            <pre className="text-body-xs text-text-muted overflow-auto max-h-64">
              An error occurred in the application.
            </pre>
          </details>
        )}

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
          <button
            onClick={() => window.location.reload()}
            className={cn(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors',
              'border border-border-default text-text-secondary hover:bg-bg-elevated'
            )}
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    </div>
  );
}
