'use client';

import { useOnlineStatus, useServiceWorker } from '@/hooks/use-online-status';
import { WifiOff, RefreshCw, X } from 'lucide-react';
import { useState, useEffect } from 'react';

/**
 * Displays an offline indicator banner when the user loses internet connection.
 * Also shows a notification when an app update is available.
 */
export function OfflineIndicator() {
  const { isOffline, wasOffline, isOnline } = useOnlineStatus();
  const { updateAvailable, skipWaiting } = useServiceWorker();
  const [showReconnected, setShowReconnected] = useState(false);
  const [dismissedUpdate, setDismissedUpdate] = useState(false);

  // Show "reconnected" message briefly when coming back online
  useEffect(() => {
    if (isOnline && wasOffline) {
      setShowReconnected(true);
      const timer = setTimeout(() => {
        setShowReconnected(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isOnline, wasOffline]);

  // Offline banner
  if (isOffline) {
    return (
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-amber-500 text-white px-4 py-3 shadow-lg"
        role="alert"
        aria-live="polite"
      >
        <div className="max-w-4xl mx-auto flex items-center justify-center gap-3">
          <WifiOff className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <span className="text-sm font-medium">
            You&apos;re offline. Some features may be limited.
          </span>
        </div>
      </div>
    );
  }

  // Reconnected notification
  if (showReconnected) {
    return (
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-green-500 text-white px-4 py-3 shadow-lg"
        role="alert"
        aria-live="polite"
      >
        <div className="max-w-4xl mx-auto flex items-center justify-center gap-3">
          <RefreshCw className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <span className="text-sm font-medium">
            You&apos;re back online!
          </span>
        </div>
      </div>
    );
  }

  // Update available notification
  if (updateAvailable && !dismissedUpdate) {
    return (
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-blue-500 text-white px-4 py-3 shadow-lg"
        role="alert"
        aria-live="polite"
      >
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <RefreshCw className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
            <span className="text-sm font-medium">
              A new version is available!
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={skipWaiting}
              className="bg-white text-blue-500 px-3 py-1 rounded text-sm font-medium hover:bg-blue-50 transition-colors"
            >
              Update now
            </button>
            <button
              onClick={() => setDismissedUpdate(true)}
              className="p-1 hover:bg-blue-400 rounded transition-colors"
              aria-label="Dismiss update notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/**
 * Wrapper component that adds offline-aware styling and behavior.
 * Use this to wrap content that should be visually muted when offline.
 */
export function OfflineAware({ children }: { children: React.ReactNode }) {
  const { isOffline } = useOnlineStatus();

  return (
    <div className={isOffline ? 'opacity-75 pointer-events-none' : ''}>
      {children}
    </div>
  );
}

/**
 * Component that only renders its children when online.
 * Shows a fallback message when offline.
 */
export function OnlineOnly({
  children,
  fallback,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { isOffline } = useOnlineStatus();

  if (isOffline) {
    return (
      fallback || (
        <div className="text-center py-8 text-gray-500">
          <WifiOff className="h-8 w-8 mx-auto mb-2" />
          <p>This feature requires an internet connection.</p>
        </div>
      )
    );
  }

  return <>{children}</>;
}
