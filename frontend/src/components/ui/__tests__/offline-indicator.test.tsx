import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OfflineIndicator, OfflineAware, OnlineOnly } from '../offline-indicator';

// Mock the hooks
const mockOnlineStatus = {
  isOnline: true,
  isOffline: false,
  wasOffline: false,
};

const mockServiceWorker = {
  registration: null,
  updateAvailable: false,
  skipWaiting: vi.fn(),
  clearCache: vi.fn(),
};

vi.mock('@/hooks/use-online-status', () => ({
  useOnlineStatus: () => mockOnlineStatus,
  useServiceWorker: () => mockServiceWorker,
}));

describe('OfflineIndicator', () => {
  beforeEach(() => {
    // Reset to default online state
    mockOnlineStatus.isOnline = true;
    mockOnlineStatus.isOffline = false;
    mockOnlineStatus.wasOffline = false;
    mockServiceWorker.updateAvailable = false;
    mockServiceWorker.skipWaiting.mockClear();
  });

  it('should render nothing when online and no updates available', () => {
    const { container } = render(<OfflineIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it('should show offline banner when offline', () => {
    mockOnlineStatus.isOnline = false;
    mockOnlineStatus.isOffline = true;

    render(<OfflineIndicator />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/you're offline/i)).toBeInTheDocument();
    expect(screen.getByText(/some features may be limited/i)).toBeInTheDocument();
  });

  it('should show update available banner when update is ready', () => {
    mockServiceWorker.updateAvailable = true;

    render(<OfflineIndicator />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/a new version is available/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /update now/i })).toBeInTheDocument();
  });

  it('should call skipWaiting when update button is clicked', () => {
    mockServiceWorker.updateAvailable = true;

    render(<OfflineIndicator />);

    fireEvent.click(screen.getByRole('button', { name: /update now/i }));

    expect(mockServiceWorker.skipWaiting).toHaveBeenCalled();
  });

  it('should dismiss update notification when X is clicked', () => {
    mockServiceWorker.updateAvailable = true;

    render(<OfflineIndicator />);

    expect(screen.getByText(/a new version is available/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

    expect(screen.queryByText(/a new version is available/i)).not.toBeInTheDocument();
  });

  it('should have proper accessibility attributes on offline banner', () => {
    mockOnlineStatus.isOnline = false;
    mockOnlineStatus.isOffline = true;

    render(<OfflineIndicator />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('aria-live', 'polite');
  });
});

describe('OfflineAware', () => {
  beforeEach(() => {
    mockOnlineStatus.isOnline = true;
    mockOnlineStatus.isOffline = false;
  });

  it('should render children normally when online', () => {
    render(
      <OfflineAware>
        <button>Click me</button>
      </OfflineAware>
    );

    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button.parentElement).not.toHaveClass('opacity-75');
  });

  it('should apply muted styles when offline', () => {
    mockOnlineStatus.isOnline = false;
    mockOnlineStatus.isOffline = true;

    render(
      <OfflineAware>
        <button>Click me</button>
      </OfflineAware>
    );

    const button = screen.getByRole('button', { name: /click me/i });
    expect(button.parentElement).toHaveClass('opacity-75');
    expect(button.parentElement).toHaveClass('pointer-events-none');
  });
});

describe('OnlineOnly', () => {
  beforeEach(() => {
    mockOnlineStatus.isOnline = true;
    mockOnlineStatus.isOffline = false;
  });

  it('should render children when online', () => {
    render(
      <OnlineOnly>
        <div data-testid="online-content">Online content</div>
      </OnlineOnly>
    );

    expect(screen.getByTestId('online-content')).toBeInTheDocument();
  });

  it('should render default fallback when offline', () => {
    mockOnlineStatus.isOnline = false;
    mockOnlineStatus.isOffline = true;

    render(
      <OnlineOnly>
        <div data-testid="online-content">Online content</div>
      </OnlineOnly>
    );

    expect(screen.queryByTestId('online-content')).not.toBeInTheDocument();
    expect(screen.getByText(/this feature requires an internet connection/i)).toBeInTheDocument();
  });

  it('should render custom fallback when offline', () => {
    mockOnlineStatus.isOnline = false;
    mockOnlineStatus.isOffline = true;

    render(
      <OnlineOnly fallback={<div data-testid="custom-fallback">Custom offline message</div>}>
        <div data-testid="online-content">Online content</div>
      </OnlineOnly>
    );

    expect(screen.queryByTestId('online-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.getByText(/custom offline message/i)).toBeInTheDocument();
  });
});
