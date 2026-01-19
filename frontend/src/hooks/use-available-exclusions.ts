'use client';

import { useQuery } from '@tanstack/react-query';
import { authApi } from '@/lib/api';
import { DietaryExclusionOption } from '@/types';

/**
 * Query key for available dietary exclusions.
 * Centralized to ensure consistent cache invalidation.
 */
export const EXCLUSIONS_QUERY_KEY = ['availableExclusions'] as const;

/**
 * Default stale time for exclusions data: 24 hours.
 * Since dietary exclusions are static configuration data (backed by an enum),
 * they rarely change and can be cached aggressively.
 */
const EXCLUSIONS_STALE_TIME = 1000 * 60 * 60 * 24; // 24 hours

/**
 * Default cache time (gcTime): 7 days.
 * Keep data in cache even when no components are subscribed.
 */
const EXCLUSIONS_GC_TIME = 1000 * 60 * 60 * 24 * 7; // 7 days

interface UseAvailableExclusionsResult {
  exclusions: DietaryExclusionOption[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Hook to fetch and cache available dietary exclusion options.
 *
 * Benefits:
 * - Cached for 24 hours (staleTime) - avoids refetching on every page load
 * - Shared across components - register page and settings use same cache
 * - Automatic background refetching when stale
 * - Deduplication - concurrent mounts don't trigger multiple requests
 *
 * Usage:
 * ```tsx
 * const { exclusions, isLoading } = useAvailableExclusions();
 * ```
 */
export function useAvailableExclusions(): UseAvailableExclusionsResult {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: EXCLUSIONS_QUERY_KEY,
    queryFn: async () => {
      const response = await authApi.getAvailableExclusions();
      return response.data.exclusions as DietaryExclusionOption[];
    },
    staleTime: EXCLUSIONS_STALE_TIME,
    gcTime: EXCLUSIONS_GC_TIME,
    // Refetch on window focus disabled since data is static
    refetchOnWindowFocus: false,
    // Keep previous data while refetching for seamless UX
    placeholderData: (previousData) => previousData,
  });

  return {
    exclusions: data ?? [],
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
  };
}
