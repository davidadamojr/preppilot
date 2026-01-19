'use client';

import { useQuery } from '@tanstack/react-query';
import { featureFlagsApi } from '@/lib/api';
import { featureFlagKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import type { FeatureName, FeatureFlagsResponse } from '@/types';

/**
 * Default stale time for feature flags: 5 minutes.
 * Feature flags may change during a session, so we refresh periodically.
 */
const FLAGS_STALE_TIME = 1000 * 60 * 5; // 5 minutes

/**
 * Default cache time (gcTime): 30 minutes.
 * Keep flags in cache even when no components are subscribed.
 */
const FLAGS_GC_TIME = 1000 * 60 * 30; // 30 minutes

/**
 * Default feature flag state - all features enabled.
 * Used when flags are loading or if fetch fails.
 * This ensures the app remains functional even if flag fetch fails.
 */
const DEFAULT_FLAGS: Record<FeatureName, boolean> = {
  email_plan_notifications: true,
  email_expiring_alerts: true,
  email_adaptation_summaries: true,
  export_pdf: true,
  export_shopping_list: true,
  plan_duplication: true,
  plan_adaptation: true,
  meal_swap: true,
  fridge_bulk_import: true,
  fridge_expiring_notifications: true,
  recipe_search: true,
  recipe_browser: true,
  admin_user_management: true,
  admin_audit_logs: true,
  prep_timeline_optimization: true,
  llm_step_parsing: true,
  offline_mode: true,
};

interface UseFeatureFlagsResult {
  /** Map of feature names to their enabled state */
  flags: Record<FeatureName, boolean>;
  /** Whether the flags are currently loading */
  isLoading: boolean;
  /** Whether fetching flags failed */
  isError: boolean;
  /** The error if fetch failed */
  error: Error | null;
  /** Check if a specific feature is enabled */
  isEnabled: (feature: FeatureName) => boolean;
  /** Refetch feature flags */
  refetch: () => void;
}

/**
 * Hook to fetch and cache feature flags for the current user.
 *
 * Benefits:
 * - Cached for 5 minutes (staleTime) - avoids excessive refetching
 * - Scoped by userId - cache cleared on logout
 * - Returns default (all enabled) while loading - graceful degradation
 * - Provides isEnabled helper for easy feature checks
 *
 * Usage:
 * ```tsx
 * const { flags, isEnabled } = useFeatureFlags();
 *
 * // Check if a feature is enabled
 * if (isEnabled('plan_duplication')) {
 *   // Show duplicate button
 * }
 *
 * // Or access flags directly
 * {flags.plan_duplication && <DuplicateButton />}
 * ```
 */
export function useFeatureFlags(): UseFeatureFlagsResult {
  const { user } = useAuth();
  const userId = user?.id;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: featureFlagKeys.flags(userId),
    queryFn: async () => {
      const response = await featureFlagsApi.getAll();
      return (response.data as FeatureFlagsResponse).flags;
    },
    staleTime: FLAGS_STALE_TIME,
    gcTime: FLAGS_GC_TIME,
    // Only fetch when user is logged in
    enabled: !!userId,
    // Keep previous data while refetching for seamless UX
    placeholderData: (previousData) => previousData,
    // Don't refetch on window focus - flags rarely change mid-session
    refetchOnWindowFocus: false,
  });

  // Merge fetched flags with defaults (in case backend adds new flags)
  const flags: Record<FeatureName, boolean> = {
    ...DEFAULT_FLAGS,
    ...(data ?? {}),
  };

  const isEnabled = (feature: FeatureName): boolean => {
    return flags[feature] ?? true;
  };

  return {
    flags,
    isLoading,
    isError,
    error: error as Error | null,
    isEnabled,
    refetch,
  };
}

/**
 * Check if an error is a FEATURE_DISABLED error from the backend.
 *
 * When a feature is disabled, the backend returns:
 * - HTTP 503 Service Unavailable
 * - Body: { error_code: 'FEATURE_DISABLED', message: '...', feature: '...' }
 *
 * Usage:
 * ```tsx
 * try {
 *   await plansApi.duplicate(id, date);
 * } catch (error) {
 *   if (isFeatureDisabledError(error)) {
 *     toast.info(`${error.feature} is currently unavailable`);
 *   } else {
 *     toast.error('Failed to duplicate plan');
 *   }
 * }
 * ```
 */
export function isFeatureDisabledError(
  error: unknown
): error is { response: { status: 503; data: { detail: { error_code: 'FEATURE_DISABLED'; message: string; feature: FeatureName } } } } {
  if (typeof error !== 'object' || error === null) return false;

  const axiosError = error as {
    response?: {
      status?: number;
      data?: { detail?: { error_code?: string } };
    };
  };

  return (
    axiosError.response?.status === 503 &&
    axiosError.response?.data?.detail?.error_code === 'FEATURE_DISABLED'
  );
}

/**
 * Get user-friendly message for a disabled feature.
 */
export function getFeatureDisabledMessage(feature: FeatureName): string {
  const featureLabels: Record<FeatureName, string> = {
    email_plan_notifications: 'Email notifications',
    email_expiring_alerts: 'Expiring item alerts',
    email_adaptation_summaries: 'Adaptation summaries',
    export_pdf: 'PDF export',
    export_shopping_list: 'Shopping list export',
    plan_duplication: 'Plan duplication',
    plan_adaptation: 'Plan adaptation',
    meal_swap: 'Meal swapping',
    fridge_bulk_import: 'Bulk import',
    fridge_expiring_notifications: 'Expiring notifications',
    recipe_search: 'Recipe search',
    recipe_browser: 'Recipe browser',
    admin_user_management: 'User management',
    admin_audit_logs: 'Audit logs',
    prep_timeline_optimization: 'Prep timeline optimization',
    llm_step_parsing: 'LLM step parsing',
    offline_mode: 'Offline mode',
  };

  const label = featureLabels[feature] || feature.replace(/_/g, ' ');
  return `${label} is currently unavailable`;
}
