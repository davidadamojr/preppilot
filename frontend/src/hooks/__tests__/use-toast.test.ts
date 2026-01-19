import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useToast, toast, reducer } from '../use-toast';

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('reducer', () => {
    it('should add a toast', () => {
      const initialState = { toasts: [] };
      const newToast = {
        id: '1',
        title: 'Test Toast',
        description: 'Test description',
        open: true,
      };

      const result = reducer(initialState, {
        type: 'ADD_TOAST',
        toast: newToast,
      });

      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0]).toEqual(newToast);
    });

    it('should limit toasts to TOAST_LIMIT (1)', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'First', open: true }],
      };

      const result = reducer(initialState, {
        type: 'ADD_TOAST',
        toast: { id: '2', title: 'Second', open: true },
      });

      // Only the newest toast should remain (limit is 1)
      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0].title).toBe('Second');
    });

    it('should update a toast', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'Original', open: true }],
      };

      const result = reducer(initialState, {
        type: 'UPDATE_TOAST',
        toast: { id: '1', title: 'Updated' },
      });

      expect(result.toasts[0].title).toBe('Updated');
      expect(result.toasts[0].open).toBe(true);
    });

    it('should not update non-matching toast', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'Original', open: true }],
      };

      const result = reducer(initialState, {
        type: 'UPDATE_TOAST',
        toast: { id: '999', title: 'Updated' },
      });

      expect(result.toasts[0].title).toBe('Original');
    });

    it('should dismiss a specific toast by setting open to false', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'Test', open: true }],
      };

      const result = reducer(initialState, {
        type: 'DISMISS_TOAST',
        toastId: '1',
      });

      expect(result.toasts[0].open).toBe(false);
    });

    it('should dismiss all toasts when no toastId provided', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'First', open: true }],
      };

      const result = reducer(initialState, {
        type: 'DISMISS_TOAST',
        toastId: undefined,
      });

      result.toasts.forEach((t) => {
        expect(t.open).toBe(false);
      });
    });

    it('should remove a specific toast from array', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'Test', open: true }],
      };

      const result = reducer(initialState, {
        type: 'REMOVE_TOAST',
        toastId: '1',
      });

      expect(result.toasts).toHaveLength(0);
    });

    it('should remove all toasts when no toastId provided', () => {
      const initialState = {
        toasts: [{ id: '1', title: 'Test', open: true }],
      };

      const result = reducer(initialState, {
        type: 'REMOVE_TOAST',
        toastId: undefined,
      });

      expect(result.toasts).toHaveLength(0);
    });
  });

  describe('toast function', () => {
    it('should create a toast with title and description', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        toast({
          title: 'Success',
          description: 'Operation completed',
        });
      });

      expect(result.current.toasts).toHaveLength(1);
      expect(result.current.toasts[0].title).toBe('Success');
      expect(result.current.toasts[0].description).toBe('Operation completed');
      expect(result.current.toasts[0].open).toBe(true);

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });

    it('should return dismiss and update functions', () => {
      const { result } = renderHook(() => useToast());

      let toastResult: ReturnType<typeof toast>;
      act(() => {
        toastResult = toast({ title: 'Test' });
      });

      expect(typeof toastResult!.dismiss).toBe('function');
      expect(typeof toastResult!.update).toBe('function');
      expect(typeof toastResult!.id).toBe('string');

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });

    it('should dismiss toast when calling returned dismiss function', () => {
      const { result } = renderHook(() => useToast());

      let toastResult: ReturnType<typeof toast>;
      act(() => {
        toastResult = toast({ title: 'Test' });
      });

      act(() => {
        toastResult!.dismiss();
      });

      expect(result.current.toasts[0].open).toBe(false);

      // Clean up
      act(() => {
        vi.advanceTimersByTime(6000);
      });
    });

    it('should update toast when calling returned update function', () => {
      const { result } = renderHook(() => useToast());

      let toastResult: ReturnType<typeof toast>;
      act(() => {
        toastResult = toast({ title: 'Original' });
      });

      act(() => {
        toastResult!.update({ title: 'Updated', id: toastResult!.id });
      });

      expect(result.current.toasts[0].title).toBe('Updated');

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });

    it('should generate unique IDs for each toast', () => {
      const { result } = renderHook(() => useToast());

      let toast1Id: string;
      let toast2Id: string;

      act(() => {
        const t1 = toast({ title: 'First' });
        toast1Id = t1.id;
        t1.dismiss();
      });

      act(() => {
        vi.advanceTimersByTime(6000);
      });

      act(() => {
        const t2 = toast({ title: 'Second' });
        toast2Id = t2.id;
      });

      expect(toast1Id!).not.toBe(toast2Id!);

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });
  });

  describe('useToast hook', () => {
    it('should provide current toasts state', () => {
      const { result } = renderHook(() => useToast());

      expect(result.current.toasts).toBeDefined();
      expect(Array.isArray(result.current.toasts)).toBe(true);
    });

    it('should provide toast function', () => {
      const { result } = renderHook(() => useToast());

      expect(typeof result.current.toast).toBe('function');
    });

    it('should provide dismiss function', () => {
      const { result } = renderHook(() => useToast());

      expect(typeof result.current.dismiss).toBe('function');
    });

    it('should dismiss specific toast by ID', () => {
      const { result } = renderHook(() => useToast());

      let toastId: string;
      act(() => {
        const t = toast({ title: 'Test' });
        toastId = t.id;
      });

      act(() => {
        result.current.dismiss(toastId!);
      });

      expect(result.current.toasts[0].open).toBe(false);

      // Clean up
      act(() => {
        vi.advanceTimersByTime(6000);
      });
    });

    it('should dismiss all toasts when called without ID', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        toast({ title: 'Test' });
      });

      act(() => {
        result.current.dismiss();
      });

      result.current.toasts.forEach((t) => {
        expect(t.open).toBe(false);
      });

      // Clean up
      act(() => {
        vi.advanceTimersByTime(6000);
      });
    });

    it('should sync state across multiple hook instances', () => {
      const { result: hook1 } = renderHook(() => useToast());
      const { result: hook2 } = renderHook(() => useToast());

      act(() => {
        hook1.current.toast({ title: 'Shared Toast' });
      });

      // Both hooks should see the same toast
      expect(hook1.current.toasts.length).toBe(hook2.current.toasts.length);
      expect(hook1.current.toasts[0]?.title).toBe('Shared Toast');

      // Clean up
      act(() => {
        hook1.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });
  });

  describe('toast variants', () => {
    it('should support destructive variant', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        toast({
          title: 'Error',
          description: 'Something went wrong',
          variant: 'destructive',
        });
      });

      expect(result.current.toasts[0].variant).toBe('destructive');

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });

    it('should support default variant', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        toast({
          title: 'Info',
          variant: 'default',
        });
      });

      expect(result.current.toasts[0].variant).toBe('default');

      // Clean up
      act(() => {
        result.current.dismiss();
        vi.advanceTimersByTime(6000);
      });
    });
  });
});
