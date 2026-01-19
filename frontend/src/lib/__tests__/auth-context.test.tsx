import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AxiosResponse } from 'axios';
import { AuthProvider, useAuth } from '../auth-context';
import { authApi } from '../api';
import { createUser } from '@/test/factories';
import type { User } from '@/types';

// Mock the API module
vi.mock('../api', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    getProfile: vi.fn(),
    updateExclusions: vi.fn(),
  },
}));

const mockAuthApi = vi.mocked(authApi);

// Helper to create mock Axios response
function mockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as AxiosResponse['config'],
  };
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset localStorage mock
    vi.mocked(window.localStorage.getItem).mockReturnValue(null);
    vi.mocked(window.localStorage.setItem).mockImplementation(() => {});
    vi.mocked(window.localStorage.removeItem).mockImplementation(() => {});
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('useAuth hook', () => {
    it('should throw error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useAuth());
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });

    it('should provide auth context when wrapped in AuthProvider', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(typeof result.current.login).toBe('function');
      expect(typeof result.current.register).toBe('function');
      expect(typeof result.current.logout).toBe('function');
      expect(typeof result.current.updateExclusions).toBe('function');
    });
  });

  describe('initialization', () => {
    it('should have loading state that resolves to false', async () => {
      // Note: Due to useEffect running synchronously in tests,
      // we test that loading eventually becomes false rather than
      // testing initial state which is implementation-dependent
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('should set loading to false when no token in localStorage', async () => {
      vi.mocked(window.localStorage.getItem).mockReturnValue(null);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
    });

    it('should fetch user profile when token exists in localStorage', async () => {
      const mockUser = createUser({ email: 'stored@example.com' });
      vi.mocked(window.localStorage.getItem).mockReturnValue('stored-token');
      mockAuthApi.getProfile.mockResolvedValue(mockAxiosResponse(mockUser));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockAuthApi.getProfile).toHaveBeenCalled();
      expect(result.current.user).toEqual(mockUser);
    });

    it('should clear token and set loading false when profile fetch fails', async () => {
      vi.mocked(window.localStorage.getItem).mockReturnValue('invalid-token');
      mockAuthApi.getProfile.mockRejectedValue({
        response: { status: 401 },
        message: 'Unauthorized',
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(window.localStorage.removeItem).toHaveBeenCalledWith('token');
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
    });
  });

  describe('login', () => {
    it('should login successfully and fetch user profile', async () => {
      const mockUser = createUser({ email: 'test@example.com' });
      const mockToken = 'jwt-token-123';

      mockAuthApi.login.mockResolvedValue(
        mockAxiosResponse({ access_token: mockToken })
      );
      mockAuthApi.getProfile.mockResolvedValue(mockAxiosResponse(mockUser));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login('test@example.com', 'password123');
      });

      expect(mockAuthApi.login).toHaveBeenCalledWith('test@example.com', 'password123');
      expect(window.localStorage.setItem).toHaveBeenCalledWith('token', mockToken);
      expect(mockAuthApi.getProfile).toHaveBeenCalled();
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.token).toBe(mockToken);
    });

    it('should throw error when login fails', async () => {
      const loginError = new Error('Invalid credentials');
      mockAuthApi.login.mockRejectedValue(loginError);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.login('wrong@example.com', 'wrongpassword');
        })
      ).rejects.toThrow('Invalid credentials');
    });
  });

  describe('register', () => {
    it('should register and then login automatically', async () => {
      const mockUser = createUser({ email: 'new@example.com', diet_type: 'fodmap' });
      const mockToken = 'new-jwt-token';

      mockAuthApi.register.mockResolvedValue(mockAxiosResponse({}));
      mockAuthApi.login.mockResolvedValue(
        mockAxiosResponse({ access_token: mockToken })
      );
      mockAuthApi.getProfile.mockResolvedValue(mockAxiosResponse(mockUser));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.register('new@example.com', 'password123', 'vegetarian', ['gluten']);
      });

      expect(mockAuthApi.register).toHaveBeenCalledWith(
        'new@example.com',
        'password123',
        'vegetarian',
        ['gluten']
      );
      expect(mockAuthApi.login).toHaveBeenCalledWith('new@example.com', 'password123');
      expect(result.current.user).toEqual(mockUser);
    });

    it('should register with empty dietary exclusions by default', async () => {
      const mockUser = createUser();
      const mockToken = 'jwt-token';

      mockAuthApi.register.mockResolvedValue(mockAxiosResponse({}));
      mockAuthApi.login.mockResolvedValue(
        mockAxiosResponse({ access_token: mockToken })
      );
      mockAuthApi.getProfile.mockResolvedValue(mockAxiosResponse(mockUser));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.register('test@example.com', 'password123', 'omnivore');
      });

      expect(mockAuthApi.register).toHaveBeenCalledWith(
        'test@example.com',
        'password123',
        'omnivore',
        []
      );
    });

    it('should throw error when registration fails', async () => {
      const registerError = new Error('Email already exists');
      mockAuthApi.register.mockRejectedValue(registerError);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.register('existing@example.com', 'password123', 'omnivore');
        })
      ).rejects.toThrow('Email already exists');
    });
  });

  describe('updateExclusions', () => {
    it('should update exclusions and refresh user profile', async () => {
      const mockUser = createUser({ dietary_exclusions: [] });
      const updatedUser: User = { ...mockUser, dietary_exclusions: ['gluten', 'dairy'] };
      const mockToken = 'jwt-token';

      vi.mocked(window.localStorage.getItem).mockReturnValue(mockToken);
      mockAuthApi.getProfile
        .mockResolvedValueOnce(mockAxiosResponse(mockUser))
        .mockResolvedValueOnce(mockAxiosResponse(updatedUser));
      mockAuthApi.updateExclusions.mockResolvedValue(mockAxiosResponse({}));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.updateExclusions(['gluten', 'dairy']);
      });

      expect(mockAuthApi.updateExclusions).toHaveBeenCalledWith(['gluten', 'dairy']);
      expect(result.current.user?.dietary_exclusions).toEqual(['gluten', 'dairy']);
    });

    it('should throw error when update fails', async () => {
      const updateError = new Error('Update failed');
      mockAuthApi.updateExclusions.mockRejectedValue(updateError);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.updateExclusions(['invalid']);
        })
      ).rejects.toThrow('Update failed');
    });
  });

  describe('logout', () => {
    it('should clear user, token, and localStorage', async () => {
      const mockUser = createUser();
      const mockToken = 'jwt-token';

      vi.mocked(window.localStorage.getItem).mockReturnValue(mockToken);
      mockAuthApi.getProfile.mockResolvedValue(mockAxiosResponse(mockUser));

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      act(() => {
        result.current.logout();
      });

      expect(window.localStorage.removeItem).toHaveBeenCalledWith('token');
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
    });

    it('should work even when user is already logged out', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should not throw
      act(() => {
        result.current.logout();
      });

      expect(window.localStorage.removeItem).toHaveBeenCalledWith('token');
      expect(result.current.user).toBeNull();
    });
  });
});
