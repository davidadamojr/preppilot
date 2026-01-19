'use client';

import { WifiOff, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { useOnlineStatus } from '@/hooks/use-online-status';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Offline fallback page displayed when the user navigates
 * while offline and the page is not cached.
 */
export default function OfflinePage() {
  const { isOnline } = useOnlineStatus();
  const router = useRouter();

  // Redirect to home when back online
  useEffect(() => {
    if (isOnline) {
      router.push('/');
    }
  }, [isOnline, router]);

  const handleRetry = () => {
    window.location.reload();
  };

  return (
    <main id="main-content" className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-amber-100 mb-4">
            <WifiOff className="w-10 h-10 text-amber-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            You&apos;re Offline
          </h1>
          <p className="text-gray-600">
            It looks like you&apos;ve lost your internet connection. Some features
            may not be available until you&apos;re back online.
          </p>
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <h2 className="font-medium text-gray-900 mb-3">
              What you can still do:
            </h2>
            <ul className="text-left text-sm text-gray-600 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">✓</span>
                View your cached meal plans
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">✓</span>
                Browse saved recipes
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">✓</span>
                Check your fridge inventory
              </li>
            </ul>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleRetry}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
            <Link
              href="/"
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Home className="w-4 h-4" />
              Go Home
            </Link>
          </div>
        </div>

        <p className="mt-8 text-sm text-gray-500">
          We&apos;ll automatically reconnect when your connection is restored.
        </p>
      </div>
    </main>
  );
}
