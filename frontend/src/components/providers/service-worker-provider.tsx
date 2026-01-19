'use client';

import { useEffect } from 'react';
import { OfflineIndicator } from '@/components/ui/offline-indicator';

/**
 * Provider component that registers the service worker and renders
 * the offline indicator. Must be used within a client component context.
 */
export function ServiceWorkerProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    // Register service worker
    const registerServiceWorker = async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
        });

        // Log successful registration
        if (process.env.NODE_ENV === 'development') {
          console.log('Service Worker registered:', registration.scope);
        }

        // Handle controller change (new service worker activated)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          // Optionally reload when a new service worker takes control
          // window.location.reload();
        });
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    };

    registerServiceWorker();
  }, []);

  return (
    <>
      {children}
      <OfflineIndicator />
    </>
  );
}
