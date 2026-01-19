'use client';

import { QueryClient, QueryClientProvider, onlineManager } from '@tanstack/react-query';
import { ReactNode, useState, useEffect } from 'react';

/**
 * Configure React Query for offline-first behavior.
 *
 * Strategy:
 * - Longer stale times to reduce unnecessary refetches
 * - Pause queries when offline, resume when online
 * - Cache data persists across page reloads via service worker
 * - Retry with exponential backoff
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Keep data fresh for 5 minutes (reduces refetches)
            staleTime: 5 * 60 * 1000,
            // Cache data for 30 minutes (offline fallback)
            gcTime: 30 * 60 * 1000,
            // Retry failed requests with exponential backoff
            retry: 3,
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
            // Don't refetch on window focus when offline
            refetchOnWindowFocus: true,
            // Pause queries when offline
            networkMode: 'offlineFirst',
          },
          mutations: {
            // Retry mutations once
            retry: 1,
            // Pause mutations when offline
            networkMode: 'offlineFirst',
          },
        },
      })
  );

  // Sync online manager with browser online status
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Set initial online state
    onlineManager.setOnline(navigator.onLine);

    const handleOnline = () => onlineManager.setOnline(true);
    const handleOffline = () => onlineManager.setOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
