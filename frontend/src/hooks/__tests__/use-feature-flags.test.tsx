import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFeatureFlags, isFeatureDisabledError, getFeatureDisabledMessage } from '../use-feature-flags';
import { featureFlagsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { ReactNode } from 'react';

// Mock the API
jest.mock('@/lib/api', () => ({
  featureFlagsApi: {
    getAll: jest.fn(),
  },
}));

// Mock the auth context
jest.mock('@/lib/auth-context', () => ({
  useAuth: jest.fn(),
}));

const mockedFeatureFlagsApi = featureFlagsApi as jest.Mocked<typeof featureFlagsApi>;
const mockedUseAuth = useAuth as jest.Mock;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('useFeatureFlags', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      user: { id: 'user-123', email: 'test@example.com' },
    });
  });

  it('should return default flags while loading', () => {
    mockedFeatureFlagsApi.getAll.mockReturnValue(new Promise(() => {})); // Never resolves

    const { result } = renderHook(() => useFeatureFlags(), {
      wrapper: createWrapper(),
    });

    // Should have all default flags as true
    expect(result.current.flags.plan_duplication).toBe(true);
    expect(result.current.flags.meal_swap).toBe(true);
    expect(result.current.flags.export_pdf).toBe(true);
    expect(result.current.isLoading).toBe(true);
  });

  it('should fetch and return flags from API', async () => {
    const mockFlags = {
      plan_duplication: true,
      meal_swap: false,
      export_pdf: true,
      export_shopping_list: true,
      fridge_bulk_import: false,
      plan_adaptation: true,
      email_plan_notifications: true,
      email_expiring_alerts: true,
      email_adaptation_summaries: true,
      fridge_expiring_notifications: true,
      recipe_search: true,
      recipe_browser: true,
      admin_user_management: true,
      admin_audit_logs: true,
      prep_timeline_optimization: true,
      offline_mode: true,
    };

    mockedFeatureFlagsApi.getAll.mockResolvedValue({
      data: { flags: mockFlags },
    });

    const { result } = renderHook(() => useFeatureFlags(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.flags.plan_duplication).toBe(true);
    expect(result.current.flags.meal_swap).toBe(false);
    expect(result.current.flags.fridge_bulk_import).toBe(false);
  });

  it('should provide isEnabled helper function', async () => {
    const mockFlags = {
      plan_duplication: true,
      meal_swap: false,
      export_pdf: true,
      export_shopping_list: true,
      fridge_bulk_import: true,
      plan_adaptation: true,
      email_plan_notifications: true,
      email_expiring_alerts: true,
      email_adaptation_summaries: true,
      fridge_expiring_notifications: true,
      recipe_search: true,
      recipe_browser: true,
      admin_user_management: true,
      admin_audit_logs: true,
      prep_timeline_optimization: true,
      offline_mode: true,
    };

    mockedFeatureFlagsApi.getAll.mockResolvedValue({
      data: { flags: mockFlags },
    });

    const { result } = renderHook(() => useFeatureFlags(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isEnabled('plan_duplication')).toBe(true);
    expect(result.current.isEnabled('meal_swap')).toBe(false);
  });

  it('should not fetch when user is not logged in', () => {
    mockedUseAuth.mockReturnValue({ user: null });

    const { result } = renderHook(() => useFeatureFlags(), {
      wrapper: createWrapper(),
    });

    // Should not call API when user is null
    expect(mockedFeatureFlagsApi.getAll).not.toHaveBeenCalled();
    // Should return default flags
    expect(result.current.flags.plan_duplication).toBe(true);
  });

  it('should return default flags on API error', async () => {
    mockedFeatureFlagsApi.getAll.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useFeatureFlags(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Should still have default flags (all enabled)
    expect(result.current.flags.plan_duplication).toBe(true);
    expect(result.current.flags.meal_swap).toBe(true);
  });
});

describe('isFeatureDisabledError', () => {
  it('should return true for valid FEATURE_DISABLED error', () => {
    const error = {
      response: {
        status: 503,
        data: {
          detail: {
            error_code: 'FEATURE_DISABLED',
            message: 'Feature is disabled',
            feature: 'plan_duplication',
          },
        },
      },
    };

    expect(isFeatureDisabledError(error)).toBe(true);
  });

  it('should return false for non-503 errors', () => {
    const error = {
      response: {
        status: 500,
        data: {
          detail: {
            error_code: 'FEATURE_DISABLED',
          },
        },
      },
    };

    expect(isFeatureDisabledError(error)).toBe(false);
  });

  it('should return false for different error codes', () => {
    const error = {
      response: {
        status: 503,
        data: {
          detail: {
            error_code: 'SERVICE_UNAVAILABLE',
          },
        },
      },
    };

    expect(isFeatureDisabledError(error)).toBe(false);
  });

  it('should return false for null or undefined', () => {
    expect(isFeatureDisabledError(null)).toBe(false);
    expect(isFeatureDisabledError(undefined)).toBe(false);
  });

  it('should return false for non-object errors', () => {
    expect(isFeatureDisabledError('error string')).toBe(false);
    expect(isFeatureDisabledError(123)).toBe(false);
  });
});

describe('getFeatureDisabledMessage', () => {
  it('should return human-readable message for known features', () => {
    expect(getFeatureDisabledMessage('plan_duplication')).toBe(
      'Plan duplication is currently unavailable'
    );
    expect(getFeatureDisabledMessage('meal_swap')).toBe(
      'Meal swapping is currently unavailable'
    );
    expect(getFeatureDisabledMessage('export_pdf')).toBe(
      'PDF export is currently unavailable'
    );
    expect(getFeatureDisabledMessage('fridge_bulk_import')).toBe(
      'Bulk import is currently unavailable'
    );
  });
});
