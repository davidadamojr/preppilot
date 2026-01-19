import { useState, useEffect, useCallback } from 'react';

interface OnlineStatus {
  isOnline: boolean;
  isOffline: boolean;
  wasOffline: boolean;
}

/**
 * Hook to detect online/offline status with reconnection awareness.
 *
 * Features:
 * - Tracks current online/offline state
 * - Detects when connection is restored after being offline
 * - SSR-safe (defaults to online during server rendering)
 *
 * @returns {OnlineStatus} Current online status and history
 */
export function useOnlineStatus(): OnlineStatus {
  // Default to online for SSR
  const [isOnline, setIsOnline] = useState(true);
  const [wasOffline, setWasOffline] = useState(false);

  useEffect(() => {
    // Set initial state from navigator (client-side only)
    if (typeof navigator !== 'undefined') {
      setIsOnline(navigator.onLine);
    }

    const handleOnline = () => {
      setIsOnline(true);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    isOnline,
    isOffline: !isOnline,
    wasOffline,
  };
}

/**
 * Hook to register and manage the service worker.
 *
 * @returns Service worker registration utilities
 */
export function useServiceWorker() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const registerServiceWorker = async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
        });

        setRegistration(reg);

        // Check for updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setUpdateAvailable(true);
              }
            });
          }
        });
      } catch (error) {
        console.error('Service worker registration failed:', error);
      }
    };

    registerServiceWorker();
  }, []);

  const skipWaiting = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [registration]);

  const clearCache = useCallback(async () => {
    if (registration?.active) {
      registration.active.postMessage({ type: 'CLEAR_CACHE' });
    }
  }, [registration]);

  return {
    registration,
    updateAvailable,
    skipWaiting,
    clearCache,
  };
}
