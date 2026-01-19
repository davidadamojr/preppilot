import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import {
  ErrorBoundary,
  PlanErrorBoundary,
  FridgeErrorBoundary,
  CatchUpErrorBoundary,
  SettingsErrorBoundary,
  RecipeErrorBoundary,
  DialogErrorBoundary,
} from '../error-boundary';

// Component that throws an error on render
function ThrowingComponent({ error }: { error?: Error }): React.ReactNode {
  throw error || new Error('Test error');
}

// Component that throws on demand
function ConditionallyThrowingComponent({
  shouldThrow,
  error,
}: {
  shouldThrow: boolean;
  error?: Error;
}): React.ReactNode {
  if (shouldThrow) {
    throw error || new Error('Conditional test error');
  }
  return <div>Safe content</div>;
}

// Suppress console.error for cleaner test output
const originalError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});

afterAll(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  describe('default behavior', () => {
    it('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('renders default error UI when child throws', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(
        screen.getByText('An unexpected error occurred. Please try again.')
      ).toBeInTheDocument();
    });

    it('renders custom fallback when provided', () => {
      render(
        <ErrorBoundary fallback={<div>Custom fallback</div>}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom fallback')).toBeInTheDocument();
    });

    it('displays Try Again button with refresh icon', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Verify the Try Again button exists
      const tryAgainButton = screen.getByRole('button', { name: /try again/i });
      expect(tryAgainButton).toBeInTheDocument();
    });

    it('resets error state when Try Again is clicked', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      // Error is shown
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Click Try Again - this resets the internal state
      // The component will re-render but will throw again since the child still throws
      // This test verifies the click handler works
      const tryAgainButton = screen.getByRole('button', { name: /try again/i });
      fireEvent.click(tryAgainButton);

      // After reset and re-throw, error state is shown again
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('calls onError callback when error is caught', () => {
      const onError = vi.fn();
      const testError = new Error('Test error for callback');

      render(
        <ErrorBoundary onError={onError}>
          <ThrowingComponent error={testError} />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalledWith(
        testError,
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      );
    });

    it('calls onRetry callback when Try Again is clicked', () => {
      const onRetry = vi.fn();

      render(
        <ErrorBoundary onRetry={onRetry}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      fireEvent.click(screen.getByRole('button', { name: /try again/i }));

      expect(onRetry).toHaveBeenCalled();
    });
  });

  describe('custom props', () => {
    it('renders custom title', () => {
      render(
        <ErrorBoundary title="Custom Error Title">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom Error Title')).toBeInTheDocument();
    });

    it('renders custom description', () => {
      render(
        <ErrorBoundary description="Custom error description here.">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom error description here.')).toBeInTheDocument();
    });

    it('renders custom retry button label', () => {
      render(
        <ErrorBoundary retryLabel="Reload Data">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByRole('button', { name: /reload data/i })).toBeInTheDocument();
    });

    it('applies custom minHeight', () => {
      render(
        <ErrorBoundary minHeight="200px">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      const container = screen.getByText('Something went wrong').closest('div');
      // Check for the container with inline style
      const outerContainer = container?.closest('div[style]');
      expect(outerContainer).toHaveStyle({ minHeight: '200px' });
    });
  });
});

describe('PlanErrorBoundary', () => {
  it('renders with plan-specific error message', () => {
    render(
      <PlanErrorBoundary>
        <ThrowingComponent />
      </PlanErrorBoundary>
    );

    expect(screen.getByText('Failed to load meal plan')).toBeInTheDocument();
    expect(
      screen.getByText(/couldn't load your meal plan/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload plan/i })).toBeInTheDocument();
  });

  it('passes onError callback', () => {
    const onError = vi.fn();

    render(
      <PlanErrorBoundary onError={onError}>
        <ThrowingComponent />
      </PlanErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
  });

  it('passes onRetry callback', () => {
    const onRetry = vi.fn();

    render(
      <PlanErrorBoundary onRetry={onRetry}>
        <ThrowingComponent />
      </PlanErrorBoundary>
    );

    fireEvent.click(screen.getByRole('button', { name: /reload plan/i }));
    expect(onRetry).toHaveBeenCalled();
  });
});

describe('FridgeErrorBoundary', () => {
  it('renders with fridge-specific error message', () => {
    render(
      <FridgeErrorBoundary>
        <ThrowingComponent />
      </FridgeErrorBoundary>
    );

    expect(screen.getByText('Failed to load fridge')).toBeInTheDocument();
    expect(
      screen.getByText(/couldn't load your fridge inventory/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload fridge/i })).toBeInTheDocument();
  });
});

describe('CatchUpErrorBoundary', () => {
  it('renders with catch-up-specific error message', () => {
    render(
      <CatchUpErrorBoundary>
        <ThrowingComponent />
      </CatchUpErrorBoundary>
    );

    expect(screen.getByText('Failed to load catch-up view')).toBeInTheDocument();
    expect(
      screen.getByText(/couldn't analyze your prep status/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /check again/i })).toBeInTheDocument();
  });
});

describe('SettingsErrorBoundary', () => {
  it('renders with settings-specific error message', () => {
    render(
      <SettingsErrorBoundary>
        <ThrowingComponent />
      </SettingsErrorBoundary>
    );

    expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    expect(
      screen.getByText(/couldn't load your account settings/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload settings/i })).toBeInTheDocument();
  });
});

describe('RecipeErrorBoundary', () => {
  it('renders with recipe-specific error message', () => {
    render(
      <RecipeErrorBoundary>
        <ThrowingComponent />
      </RecipeErrorBoundary>
    );

    expect(screen.getByText('Failed to load recipes')).toBeInTheDocument();
    expect(
      screen.getByText(/couldn't load the recipe information/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload recipes/i })).toBeInTheDocument();
  });
});

describe('DialogErrorBoundary', () => {
  it('renders with compact error message for dialogs', () => {
    render(
      <DialogErrorBoundary>
        <ThrowingComponent />
      </DialogErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(
      screen.getByText(/failed to load this content/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('uses reduced minHeight for dialog context', () => {
    render(
      <DialogErrorBoundary>
        <ThrowingComponent />
      </DialogErrorBoundary>
    );

    const container = screen.getByText('Something went wrong').closest('div');
    const outerContainer = container?.closest('div[style]');
    expect(outerContainer).toHaveStyle({ minHeight: '200px' });
  });
});

describe('error isolation', () => {
  it('sibling error boundaries do not affect each other', () => {
    render(
      <div>
        <PlanErrorBoundary>
          <ThrowingComponent />
        </PlanErrorBoundary>
        <FridgeErrorBoundary>
          <div>Fridge content works</div>
        </FridgeErrorBoundary>
      </div>
    );

    // Plan boundary caught the error
    expect(screen.getByText('Failed to load meal plan')).toBeInTheDocument();
    // Fridge boundary still renders normally
    expect(screen.getByText('Fridge content works')).toBeInTheDocument();
  });
});
