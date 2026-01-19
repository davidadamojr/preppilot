import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useOnlineStatus, useServiceWorker } from '../use-online-status';

describe('useOnlineStatus', () => {
  let originalNavigator: boolean;
  let onlineListeners: Array<() => void> = [];
  let offlineListeners: Array<() => void> = [];

  beforeEach(() => {
    originalNavigator = navigator.onLine;
    onlineListeners = [];
    offlineListeners = [];

    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
      configurable: true,
    });

    // Mock addEventListener and removeEventListener
    vi.spyOn(window, 'addEventListener').mockImplementation((event, handler) => {
      if (event === 'online') {
        onlineListeners.push(handler as () => void);
      } else if (event === 'offline') {
        offlineListeners.push(handler as () => void);
      }
    });

    vi.spyOn(window, 'removeEventListener').mockImplementation((event, handler) => {
      if (event === 'online') {
        onlineListeners = onlineListeners.filter((h) => h !== handler);
      } else if (event === 'offline') {
        offlineListeners = offlineListeners.filter((h) => h !== handler);
      }
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'onLine', {
      value: originalNavigator,
      writable: true,
      configurable: true,
    });
    vi.restoreAllMocks();
  });

  it('should return online status when navigator is online', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.isOnline).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it('should return offline status when navigator is offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.isOnline).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it('should update status when going offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.isOnline).toBe(true);

    // Simulate going offline
    act(() => {
      offlineListeners.forEach((listener) => listener());
    });

    expect(result.current.isOnline).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it('should update status when coming back online', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.isOnline).toBe(false);

    // Simulate coming online
    act(() => {
      onlineListeners.forEach((listener) => listener());
    });

    expect(result.current.isOnline).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it('should track wasOffline after going offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.wasOffline).toBe(false);

    // Go offline
    act(() => {
      offlineListeners.forEach((listener) => listener());
    });

    expect(result.current.wasOffline).toBe(true);

    // Come back online - wasOffline should still be true
    act(() => {
      onlineListeners.forEach((listener) => listener());
    });

    expect(result.current.wasOffline).toBe(true);
  });

  it('should add event listeners on mount', () => {
    renderHook(() => useOnlineStatus());

    expect(window.addEventListener).toHaveBeenCalledWith('online', expect.any(Function));
    expect(window.addEventListener).toHaveBeenCalledWith('offline', expect.any(Function));
  });

  it('should remove event listeners on unmount', () => {
    const { unmount } = renderHook(() => useOnlineStatus());

    unmount();

    expect(window.removeEventListener).toHaveBeenCalledWith('online', expect.any(Function));
    expect(window.removeEventListener).toHaveBeenCalledWith('offline', expect.any(Function));
  });
});

describe('useServiceWorker', () => {
  let originalServiceWorker: ServiceWorkerContainer | undefined;

  beforeEach(() => {
    originalServiceWorker = navigator.serviceWorker;
  });

  afterEach(() => {
    if (originalServiceWorker) {
      Object.defineProperty(navigator, 'serviceWorker', {
        value: originalServiceWorker,
        configurable: true,
      });
    }
    vi.restoreAllMocks();
  });

  it('should return null registration when service worker is not supported', () => {
    // Remove serviceWorker from navigator
    Object.defineProperty(navigator, 'serviceWorker', {
      value: undefined,
      configurable: true,
    });

    const { result } = renderHook(() => useServiceWorker());

    expect(result.current.registration).toBeNull();
    expect(result.current.updateAvailable).toBe(false);
  });

  it('should attempt to register service worker when supported', async () => {
    const mockRegistration = {
      scope: '/',
      installing: null,
      waiting: null,
      active: null,
      addEventListener: vi.fn(),
    };

    const mockServiceWorker = {
      register: vi.fn().mockResolvedValue(mockRegistration),
      controller: null,
      addEventListener: vi.fn(),
    };

    Object.defineProperty(navigator, 'serviceWorker', {
      value: mockServiceWorker,
      configurable: true,
    });

    renderHook(() => useServiceWorker());

    // Wait for registration to be called
    await vi.waitFor(() => {
      expect(mockServiceWorker.register).toHaveBeenCalledWith('/sw.js', { scope: '/' });
    });
  });

  it('should provide skipWaiting function', () => {
    const { result } = renderHook(() => useServiceWorker());

    expect(typeof result.current.skipWaiting).toBe('function');
  });

  it('should provide clearCache function', () => {
    const { result } = renderHook(() => useServiceWorker());

    expect(typeof result.current.clearCache).toBe('function');
  });
});
