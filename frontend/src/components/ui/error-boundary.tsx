'use client';

import * as React from 'react';
import { Button } from './button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './card';
import { AlertCircle, CalendarX, Refrigerator, Clock, Settings, ChefHat, RefreshCw, LucideIcon } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Custom fallback element to render instead of default error UI */
  fallback?: React.ReactNode;
  /** Custom title for the error card */
  title?: string;
  /** Custom description explaining the error context */
  description?: string;
  /** Custom label for the retry button */
  retryLabel?: string;
  /** Icon to display in the error card */
  icon?: LucideIcon;
  /** Minimum height for the error container */
  minHeight?: string;
  /** Callback fired when the error boundary catches an error */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  /** Callback fired when the user clicks retry */
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary catches JavaScript errors in child components and displays a fallback UI.
 *
 * Note: React requires class components for error boundaries because the necessary
 * lifecycle methods (getDerivedStateFromError, componentDidCatch) are not available
 * as hooks. This is a fundamental React limitation.
 *
 * @example
 * // Basic usage with default fallback
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * @example
 * // Contextual error boundary with custom messaging
 * <ErrorBoundary
 *   title="Failed to load meal plan"
 *   description="We couldn't load your meal plan. Check your connection and try again."
 *   retryLabel="Reload Plan"
 *   icon={CalendarX}
 * >
 *   <PlanView />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const {
        title = 'Something went wrong',
        description = 'An unexpected error occurred. Please try again.',
        retryLabel = 'Try Again',
        icon: Icon = AlertCircle,
        minHeight = '400px',
      } = this.props;

      return (
        <div className={`flex items-center justify-center p-4`} style={{ minHeight }}>
          <Card className="w-full max-w-md">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-destructive/10 p-2">
                  <Icon className="h-5 w-5 text-destructive" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle className="text-destructive">{title}</CardTitle>
                  <CardDescription className="mt-1">
                    {description}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <pre className="overflow-auto rounded-md bg-muted p-4 text-sm">
                  {this.state.error.message}
                </pre>
              )}
              <Button onClick={this.handleReset} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
                {retryLabel}
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Pre-configured error boundaries for specific components

interface ComponentErrorBoundaryProps {
  children: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  onRetry?: () => void;
}

/**
 * Error boundary for the Plan view with contextual messaging.
 */
export function PlanErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Failed to load meal plan"
      description="We couldn't load your meal plan. This might be a temporary issue with our servers."
      retryLabel="Reload Plan"
      icon={CalendarX}
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for the Fridge view with contextual messaging.
 */
export function FridgeErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Failed to load fridge"
      description="We couldn't load your fridge inventory. Check your connection and try again."
      retryLabel="Reload Fridge"
      icon={Refrigerator}
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for the Catch-Up view with contextual messaging.
 */
export function CatchUpErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Failed to load catch-up view"
      description="We couldn't analyze your prep status. Try refreshing to see what needs attention."
      retryLabel="Check Again"
      icon={Clock}
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for the Settings view with contextual messaging.
 */
export function SettingsErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Failed to load settings"
      description="We couldn't load your account settings. Please try again."
      retryLabel="Reload Settings"
      icon={Settings}
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for recipe-related components with contextual messaging.
 */
export function RecipeErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Failed to load recipes"
      description="We couldn't load the recipe information. Please try again."
      retryLabel="Reload Recipes"
      icon={ChefHat}
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Compact error boundary for dialogs and smaller components.
 * Uses reduced min-height suitable for modal content.
 */
export function DialogErrorBoundary({ children, onError, onRetry }: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      title="Something went wrong"
      description="Failed to load this content. Please close and try again."
      retryLabel="Try Again"
      icon={AlertCircle}
      minHeight="200px"
      onError={onError}
      onRetry={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}
