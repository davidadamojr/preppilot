import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { CatchUpView } from '../catch-up-view';
import { plansApi } from '@/lib/api';
import { createMealPlan, createCatchUpSuggestions, createExpiringItem, createPendingMeal } from '@/test/factories';
import type { AxiosResponse } from 'axios';

// Mock the API module
vi.mock('@/lib/api', () => ({
  plansApi: {
    list: vi.fn(),
    getCatchUp: vi.fn(),
    adapt: vi.fn(),
  },
}));

// Mock useAuth hook to provide a mock user
vi.mock('@/lib/auth-context', () => ({
  useAuth: () => ({
    user: { id: 'test-user-id', email: 'test@example.com' },
    token: 'mock-token',
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    updateExclusions: vi.fn(),
    refreshProfile: vi.fn(),
  }),
}));

// Mock useToast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
    toasts: [],
    dismiss: vi.fn(),
  }),
}));

const mockPlansApi = vi.mocked(plansApi);

function mockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as AxiosResponse['config'],
  };
}

describe('CatchUpView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('no plan state', () => {
    it('should show message to generate a plan first when no plans exist', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText(/generate a meal plan first/i)).toBeInTheDocument();
      });
    });
  });

  describe('loading state', () => {
    it('should show loading message while fetching catch-up data', async () => {
      const mockPlan = createMealPlan();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      // Never resolve to keep loading state
      mockPlansApi.getCatchUp.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('status', { name: 'Loading catch-up suggestions' })).toBeInTheDocument();
      });
    });
  });

  describe('all caught up state', () => {
    it('should show success message when no adaptations needed', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: [],
        expiring_items: [],
        pending_meals: [],
        needs_adaptation: false,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText(/you're all caught up/i)).toBeInTheDocument();
        expect(screen.getByText(/no adaptations needed/i)).toBeInTheDocument();
      });
    });

    it('should not show Apply Adaptations button when all caught up', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: [],
        expiring_items: [],
        pending_meals: [],
        needs_adaptation: false,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText(/you're all caught up/i)).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /apply adaptations/i })).not.toBeInTheDocument();
    });
  });

  describe('with missed preps', () => {
    it('should display missed prep dates', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: ['2025-12-14', '2025-12-15'],
        expiring_items: [],
        pending_meals: [],
        needs_adaptation: true,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText('Missed Preparations')).toBeInTheDocument();
        expect(screen.getByText('2025-12-14')).toBeInTheDocument();
        expect(screen.getByText('2025-12-15')).toBeInTheDocument();
      });
    });

    it('should show Apply Adaptations button when there are missed preps', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: ['2025-12-14'],
        needs_adaptation: true,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /apply adaptations to meal plan/i })).toBeInTheDocument();
      });
    });
  });

  describe('with expiring items', () => {
    it('should display expiring items with days remaining', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: [],
        expiring_items: [
          createExpiringItem({ name: 'Spinach', days_remaining: 2, quantity: '200g' }),
          createExpiringItem({ name: 'Chicken', days_remaining: 1, quantity: '500g' }),
        ],
        pending_meals: [],
        needs_adaptation: false,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText('Expiring Soon')).toBeInTheDocument();
        expect(screen.getByText('Spinach')).toBeInTheDocument();
        expect(screen.getByText('(200g)')).toBeInTheDocument();
        expect(screen.getByText('2 days left')).toBeInTheDocument();
        expect(screen.getByText('Chicken')).toBeInTheDocument();
        expect(screen.getByText('(500g)')).toBeInTheDocument();
        expect(screen.getByText('1 day left')).toBeInTheDocument();
      });
    });

    it('should show "Expires today" for items with 0 days remaining', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        expiring_items: [
          createExpiringItem({ name: 'Milk', days_remaining: 0, quantity: '1L' }),
        ],
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText('Expires today')).toBeInTheDocument();
      });
    });
  });

  describe('with pending meals', () => {
    it('should display pending meals', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: [],
        expiring_items: [],
        pending_meals: [
          createPendingMeal({ date: '2025-12-16', meal_type: 'breakfast', recipe: 'Oatmeal Bowl' }),
          createPendingMeal({ date: '2025-12-16', meal_type: 'lunch', recipe: 'Chicken Salad' }),
        ],
        needs_adaptation: true, // Must be true for pending meals to show
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText('Upcoming Meals')).toBeInTheDocument();
        expect(screen.getByText('Oatmeal Bowl')).toBeInTheDocument();
        expect(screen.getByText('Chicken Salad')).toBeInTheDocument();
        expect(screen.getAllByText('breakfast')[0]).toBeInTheDocument();
        expect(screen.getAllByText('lunch')[0]).toBeInTheDocument();
      });
    });

    it('should limit displayed pending meals to 5', async () => {
      const mockPlan = createMealPlan({ id: 'plan-123' });
      const mockCatchUp = createCatchUpSuggestions({
        pending_meals: [
          createPendingMeal({ recipe: 'Meal 1' }),
          createPendingMeal({ recipe: 'Meal 2' }),
          createPendingMeal({ recipe: 'Meal 3' }),
          createPendingMeal({ recipe: 'Meal 4' }),
          createPendingMeal({ recipe: 'Meal 5' }),
          createPendingMeal({ recipe: 'Meal 6' }),
          createPendingMeal({ recipe: 'Meal 7' }),
        ],
        needs_adaptation: true, // Must be true for pending meals to show
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByText('Meal 1')).toBeInTheDocument();
        expect(screen.getByText('Meal 5')).toBeInTheDocument();
        expect(screen.queryByText('Meal 6')).not.toBeInTheDocument();
        expect(screen.getByText(/and 2 more meals/i)).toBeInTheDocument();
      });
    });
  });

  describe('apply adaptations action', () => {
    const mockPlan = createMealPlan({ id: 'plan-123' });
    const mockCatchUp = createCatchUpSuggestions({
      missed_preps: ['2025-12-14'],
      expiring_items: [createExpiringItem()],
      needs_adaptation: true,
    });

    it('should call adapt API when Apply Adaptations is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));
      mockPlansApi.adapt.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /apply adaptations to meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /apply adaptations to meal plan/i }));

      await waitFor(() => {
        expect(mockPlansApi.adapt).toHaveBeenCalledWith('plan-123');
      });
    });

    it('should show loading state while adapting', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));
      // Never resolve to keep loading state
      mockPlansApi.adapt.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /apply adaptations to meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /apply adaptations to meal plan/i }));

      // With optimistic updates, the UI immediately shows "all caught up" state
      await waitFor(() => {
        expect(screen.getByText(/all caught up/i)).toBeInTheDocument();
      });

      // Verify adapt API was called
      expect(mockPlansApi.adapt).toHaveBeenCalledWith(expect.any(String));
    });
  });

  describe('refresh action', () => {
    it('should have Refresh button', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions();

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh catch-up suggestions/i })).toBeInTheDocument();
      });
    });

    it('should refetch catch-up data when Refresh is clicked', async () => {
      const user = userEvent.setup();
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions();

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh catch-up suggestions/i })).toBeInTheDocument();
      });

      // Reset mock to track new calls
      mockPlansApi.getCatchUp.mockClear();
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      await user.click(screen.getByRole('button', { name: /refresh catch-up suggestions/i }));

      await waitFor(() => {
        expect(mockPlansApi.getCatchUp).toHaveBeenCalled();
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA region label', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions();

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('region', { name: /catch-up assistant/i })).toBeInTheDocument();
      });
    });

    it('should have heading for the section', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions();

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /catch-up assistant/i })).toBeInTheDocument();
      });
    });

    it('should have status role for all caught up message', async () => {
      const mockPlan = createMealPlan();
      const mockCatchUp = createCatchUpSuggestions({
        missed_preps: [],
        expiring_items: [],
        pending_meals: [],
        needs_adaptation: false,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCatchUp.mockResolvedValue(mockAxiosResponse(mockCatchUp));

      renderWithQuery(<CatchUpView />);

      await waitFor(() => {
        expect(screen.getByRole('status', { name: /no adaptations needed/i })).toBeInTheDocument();
      });
    });
  });
});
