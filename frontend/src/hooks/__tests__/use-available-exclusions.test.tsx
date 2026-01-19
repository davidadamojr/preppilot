import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useAvailableExclusions, EXCLUSIONS_QUERY_KEY } from '../use-available-exclusions';
import { authApi } from '@/lib/api';

// Mock the API
vi.mock('@/lib/api', () => ({
  authApi: {
    getAvailableExclusions: vi.fn(),
  },
}));

const mockAuthApi = authApi as unknown as {
  getAvailableExclusions: ReturnType<typeof vi.fn>;
};

const mockExclusions = [
  { name: 'Dairy', value: 'dairy' },
  { name: 'Gluten', value: 'gluten' },
  { name: 'Soy', value: 'soy' },
  { name: 'Eggs', value: 'eggs' },
];

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  });
}

function createWrapper() {
  const queryClient = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('useAvailableExclusions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('successful fetch', () => {
    it('should return exclusions from API', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValueOnce({
        data: { exclusions: mockExclusions },
      });

      const { result } = renderHook(() => useAvailableExclusions(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.exclusions).toEqual([]);

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.exclusions).toEqual(mockExclusions);
      expect(result.current.isError).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should return empty array when API returns empty exclusions', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValueOnce({
        data: { exclusions: [] },
      });

      const { result } = renderHook(() => useAvailableExclusions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.exclusions).toEqual([]);
      expect(result.current.isError).toBe(false);
    });

    it('should provide a refetch function', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue({
        data: { exclusions: mockExclusions },
      });

      const { result } = renderHook(() => useAvailableExclusions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('error handling', () => {
    it('should handle API errors', async () => {
      const testError = new Error('Network error');
      mockAuthApi.getAvailableExclusions.mockRejectedValueOnce(testError);

      const { result } = renderHook(() => useAvailableExclusions(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.exclusions).toEqual([]);
      expect(result.current.error).toEqual(testError);
    });
  });

  describe('caching behavior', () => {
    it('should share cache across multiple hook instances', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue({
        data: { exclusions: mockExclusions },
      });

      const wrapper = createWrapper();

      // First hook instance
      const { result: result1 } = renderHook(() => useAvailableExclusions(), {
        wrapper,
      });

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
      });

      // Second hook instance with same wrapper (same QueryClient)
      const { result: result2 } = renderHook(() => useAvailableExclusions(), {
        wrapper,
      });

      // Second instance should have immediate access to cached data
      // (isLoading may briefly be true but data should be available from cache)
      await waitFor(() => {
        expect(result2.current.exclusions).toEqual(mockExclusions);
      });

      // API should only have been called once due to cache sharing
      expect(mockAuthApi.getAvailableExclusions).toHaveBeenCalledTimes(1);
    });

    it('should deduplicate concurrent requests', async () => {
      let resolvePromise: (value: unknown) => void;
      const slowPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockAuthApi.getAvailableExclusions.mockReturnValue(slowPromise);

      const wrapper = createWrapper();

      // Start two hook instances simultaneously
      const { result: result1 } = renderHook(() => useAvailableExclusions(), {
        wrapper,
      });
      const { result: result2 } = renderHook(() => useAvailableExclusions(), {
        wrapper,
      });

      // Both should be loading
      expect(result1.current.isLoading).toBe(true);
      expect(result2.current.isLoading).toBe(true);

      // Resolve the promise
      resolvePromise!({ data: { exclusions: mockExclusions } });

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
        expect(result2.current.isLoading).toBe(false);
      });

      // Both should have the same data
      expect(result1.current.exclusions).toEqual(mockExclusions);
      expect(result2.current.exclusions).toEqual(mockExclusions);

      // Only one API call should have been made
      expect(mockAuthApi.getAvailableExclusions).toHaveBeenCalledTimes(1);
    });
  });

  describe('query key', () => {
    it('should export a consistent query key', () => {
      expect(EXCLUSIONS_QUERY_KEY).toEqual(['availableExclusions']);
    });
  });

  describe('return type', () => {
    it('should return all expected properties', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValueOnce({
        data: { exclusions: mockExclusions },
      });

      const { result } = renderHook(() => useAvailableExclusions(), {
        wrapper: createWrapper(),
      });

      // Check initial structure
      expect(result.current).toHaveProperty('exclusions');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('isError');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('refetch');

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Check types after loading
      expect(Array.isArray(result.current.exclusions)).toBe(true);
      expect(typeof result.current.isLoading).toBe('boolean');
      expect(typeof result.current.isError).toBe('boolean');
      expect(typeof result.current.refetch).toBe('function');
    });
  });
});
