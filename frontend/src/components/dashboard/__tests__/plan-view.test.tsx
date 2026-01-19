import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { PlanView } from '../plan-view';
import { plansApi } from '@/lib/api';
import { createMealPlan, createMealSlot, createRecipe } from '@/test/factories';
import type { AxiosResponse } from 'axios';

// Mock the API module
vi.mock('@/lib/api', () => ({
  plansApi: {
    list: vi.fn(),
    generate: vi.fn(),
    markPrep: vi.fn(),
    delete: vi.fn(),
    swapMeal: vi.fn(),
    getCompatibleRecipes: vi.fn(),
    duplicate: vi.fn(),
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

describe('PlanView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading message while fetching plans', async () => {
      // Never resolve to keep loading state
      mockPlansApi.list.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<PlanView />);

      expect(screen.getByRole('status', { name: 'Loading meal plans' })).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no plans exist', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('No meal plan yet. Generate one to get started!')).toBeInTheDocument();
      });
    });

    it('should show "Generate Plan" button when no plans exist', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generate meal plan/i })).toBeInTheDocument();
      });
    });
  });

  describe('with existing plan', () => {
    const mockPlan = createMealPlan({
      meals: [
        createMealSlot({
          meal_type: 'breakfast',
          date: '2025-01-15',
          prep_status: 'PENDING',
          recipe: createRecipe({ name: 'Oatmeal', prep_time_minutes: 10 }),
        }),
        createMealSlot({
          meal_type: 'lunch',
          date: '2025-01-15',
          prep_status: 'DONE',
          recipe: createRecipe({ name: 'Salad', prep_time_minutes: 15 }),
        }),
        createMealSlot({
          meal_type: 'dinner',
          date: '2025-01-15',
          prep_status: 'SKIPPED',
          recipe: createRecipe({ name: 'Pasta', prep_time_minutes: 30 }),
        }),
      ],
    });

    it('should display meal plan with recipes', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('Oatmeal')).toBeInTheDocument();
        expect(screen.getByText('Salad')).toBeInTheDocument();
        expect(screen.getByText('Pasta')).toBeInTheDocument();
      });
    });

    it('should display meal types', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('breakfast')).toBeInTheDocument();
        expect(screen.getByText('lunch')).toBeInTheDocument();
        expect(screen.getByText('dinner')).toBeInTheDocument();
      });
    });

    it('should display prep status badges', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('PENDING')).toBeInTheDocument();
        expect(screen.getByText('DONE')).toBeInTheDocument();
        expect(screen.getByText('SKIPPED')).toBeInTheDocument();
      });
    });

    it('should display prep time for each meal', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText(/10 min prep/)).toBeInTheDocument();
        expect(screen.getByText(/15 min prep/)).toBeInTheDocument();
        expect(screen.getByText(/30 min prep/)).toBeInTheDocument();
      });
    });

    it('should display servings when available', async () => {
      const planWithServings = createMealPlan({
        meals: [
          createMealSlot({
            meal_type: 'breakfast',
            date: '2025-01-15',
            prep_status: 'PENDING',
            recipe: createRecipe({ name: 'Oatmeal', prep_time_minutes: 10, servings: 2 }),
          }),
          createMealSlot({
            meal_type: 'lunch',
            date: '2025-01-15',
            prep_status: 'DONE',
            recipe: createRecipe({ name: 'Salad', prep_time_minutes: 15, servings: 4 }),
          }),
        ],
      });
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([planWithServings]));

      renderWithQuery(<PlanView />);

      // Check visible servings display (not sr-only descriptions)
      await waitFor(() => {
        const servingsTexts = screen.getAllByText(/2 servings/);
        expect(servingsTexts.length).toBeGreaterThan(0);
        const fourServingsTexts = screen.getAllByText(/4 servings/);
        expect(fourServingsTexts.length).toBeGreaterThan(0);
      });
    });

    it('should show "Regenerate Plan" button when plan exists', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /regenerate meal plan/i })).toBeInTheDocument();
      });
    });

    it('should show Done and Skip buttons for PENDING meals only', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        // PENDING meal should have Done and Skip buttons
        expect(screen.getByRole('button', { name: /mark breakfast as done/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /skip breakfast/i })).toBeInTheDocument();
      });

      // DONE and SKIPPED meals should not have these buttons
      expect(screen.queryByRole('button', { name: /mark lunch as done/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /mark dinner as done/i })).not.toBeInTheDocument();
    });
  });

  describe('generate plan action', () => {
    it('should call generate API when Generate Plan button is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));
      mockPlansApi.generate.mockResolvedValue(mockAxiosResponse(createMealPlan()));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /generate meal plan/i }));

      await waitFor(() => {
        expect(mockPlansApi.generate).toHaveBeenCalledWith(3);
      });
    });

    it('should disable button and show loading text while generating', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));
      // Never resolve to keep loading state
      mockPlansApi.generate.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /generate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /generating meal plan/i })).toBeDisabled();
        expect(screen.getByText('Generating...')).toBeInTheDocument();
      });
    });
  });

  describe('mark prep action', () => {
    const mockPlan = createMealPlan({
      id: 'plan-123',
      meals: [
        createMealSlot({
          meal_type: 'breakfast',
          date: '2025-01-15',
          prep_status: 'PENDING',
          recipe: createRecipe({ name: 'Oatmeal' }),
        }),
      ],
    });

    it('should call markPrep API when Done button is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.markPrep.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /mark breakfast as done/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /mark breakfast as done/i }));

      await waitFor(() => {
        expect(mockPlansApi.markPrep).toHaveBeenCalledWith(
          'plan-123',
          '2025-01-15',
          'breakfast',
          'DONE'
        );
      });
    });

    it('should call markPrep API when Skip button is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.markPrep.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /skip breakfast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /skip breakfast/i }));

      await waitFor(() => {
        expect(mockPlansApi.markPrep).toHaveBeenCalledWith(
          'plan-123',
          '2025-01-15',
          'breakfast',
          'SKIPPED'
        );
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA region label', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('region', { name: /meal plan/i })).toBeInTheDocument();
      });
    });

    it('should have heading for the section', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /meal plan/i })).toBeInTheDocument();
      });
    });
  });

  describe('delete plan action', () => {
    const mockPlan = createMealPlan({
      id: 'plan-123',
      meals: [
        createMealSlot({
          meal_type: 'breakfast',
          date: '2025-01-15',
          prep_status: 'PENDING',
          recipe: createRecipe({ name: 'Oatmeal' }),
        }),
      ],
    });

    it('should show Delete button when a plan exists', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete meal plan/i })).toBeInTheDocument();
      });
    });

    it('should not show Delete button when no plan exists', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('No meal plan yet. Generate one to get started!')).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /delete meal plan/i })).not.toBeInTheDocument();
    });

    it('should open confirmation dialog when Delete button is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /delete meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Delete Meal Plan')).toBeInTheDocument();
        expect(screen.getByText(/are you sure you want to delete this meal plan/i)).toBeInTheDocument();
      });
    });

    it('should close confirmation dialog when Cancel is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /delete meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should call delete API when Delete is confirmed', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.delete.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /delete meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Click the Delete button in the confirmation dialog
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const confirmDeleteButton = deleteButtons.find(btn => btn.closest('[role="dialog"]'));
      await user.click(confirmDeleteButton!);

      await waitFor(() => {
        expect(mockPlansApi.delete).toHaveBeenCalledWith('plan-123');
      });
    });

    it('should optimistically remove plan and close dialog when deleting', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      // Never resolve to test optimistic update
      mockPlansApi.delete.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /delete meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Click the Delete button in the confirmation dialog
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const confirmDeleteButton = deleteButtons.find(btn => btn.closest('[role="dialog"]'));
      await user.click(confirmDeleteButton!);

      // With optimistic updates, dialog closes immediately and plan disappears
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });

      // Verify delete API was called
      expect(mockPlansApi.delete).toHaveBeenCalledWith(mockPlan.id);
    });
  });

  describe('swap meal action', () => {
    const mockPlan = createMealPlan({
      id: 'plan-123',
      meals: [
        createMealSlot({
          meal_type: 'breakfast',
          date: '2025-01-15',
          prep_status: 'PENDING',
          recipe: createRecipe({ id: 'recipe-1', name: 'Oatmeal' }),
        }),
        createMealSlot({
          meal_type: 'lunch',
          date: '2025-01-15',
          prep_status: 'DONE',
          recipe: createRecipe({ id: 'recipe-2', name: 'Salad' }),
        }),
      ],
    });

    const mockCompatibleRecipes = {
      recipes: [
        {
          id: 'recipe-3',
          name: 'Pancakes',
          meal_type: 'breakfast',
          prep_time_minutes: 20,
          diet_tags: ['low-histamine'],
          servings: 2,
        },
        {
          id: 'recipe-4',
          name: 'Smoothie Bowl',
          meal_type: 'breakfast',
          prep_time_minutes: 10,
          diet_tags: ['low-histamine', 'vegan'],
          servings: 1,
        },
      ],
      total: 2,
    };

    it('should show Swap button for pending meals', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });
    });

    it('should not show Swap button for completed or skipped meals', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      // Lunch is DONE, so it shouldn't have a swap button
      expect(screen.queryByRole('button', { name: /swap lunch recipe/i })).not.toBeInTheDocument();
    });

    it('should open swap dialog when Swap button is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Swap Meal')).toBeInTheDocument();
      });
    });

    it('should display current recipe in swap dialog', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByText('Current Recipe')).toBeInTheDocument();
        // Use getAllByText since Oatmeal appears both in plan view and swap dialog
        expect(screen.getAllByText('Oatmeal').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('should load and display compatible recipes', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByText('Pancakes')).toBeInTheDocument();
        expect(screen.getByText('Smoothie Bowl')).toBeInTheDocument();
      });
    });

    it('should call swapMeal API when recipe is selected and confirmed', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));
      mockPlansApi.swapMeal.mockResolvedValue(mockAxiosResponse({ message: 'Meal swapped successfully' }));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByText('Pancakes')).toBeInTheDocument();
      });

      // Select a recipe
      await user.click(screen.getByText('Pancakes'));

      // Confirm swap
      await user.click(screen.getByRole('button', { name: /swap recipe/i }));

      await waitFor(() => {
        expect(mockPlansApi.swapMeal).toHaveBeenCalledWith(
          'plan-123',
          '2025-01-15',
          'breakfast',
          'recipe-3'
        );
      });
    });

    it('should disable swap button until a recipe is selected', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByText('Pancakes')).toBeInTheDocument();
      });

      // Swap Recipe button should be disabled initially
      expect(screen.getByRole('button', { name: /swap recipe/i })).toBeDisabled();

      // Select a recipe
      await user.click(screen.getByText('Pancakes'));

      // Now the button should be enabled
      expect(screen.getByRole('button', { name: /swap recipe/i })).toBeEnabled();
    });

    it('should close dialog when Cancel is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.getCompatibleRecipes.mockResolvedValue(mockAxiosResponse(mockCompatibleRecipes));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /swap breakfast recipe/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /swap breakfast recipe/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('duplicate plan', () => {
    const mockPlan = createMealPlan({
      meals: [
        createMealSlot({
          meal_type: 'breakfast',
          date: '2025-01-15',
          recipe: createRecipe({ name: 'Oatmeal', meal_type: 'breakfast' }),
        }),
      ],
    });

    it('should show duplicate button when plan exists', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });
    });

    it('should not show duplicate button when no plan exists', async () => {
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByText('No meal plan yet. Generate one to get started!')).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /duplicate meal plan/i })).not.toBeInTheDocument();
    });

    it('should open duplicate dialog when clicking duplicate button', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Duplicate Meal Plan')).toBeInTheDocument();
      });
    });

    it('should show original plan info in duplicate dialog', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText('Original Plan')).toBeInTheDocument();
        // Dialog shows "1 meal" - getAllByText handles sr-only descriptions
        const mealTexts = screen.getAllByText(/1 meal/);
        expect(mealTexts.length).toBeGreaterThan(0);
      });
    });

    it('should close duplicate dialog when Cancel is clicked', async () => {
      const user = userEvent.setup();
      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should call duplicate API with correct parameters', async () => {
      const user = userEvent.setup();
      const duplicatedPlan = createMealPlan({
        id: 'new-plan-id',
        start_date: '2025-01-22',
        end_date: '2025-01-24',
        meals: mockPlan.meals,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.duplicate.mockResolvedValue(mockAxiosResponse(duplicatedPlan));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Submit the form with default date
      await user.click(screen.getByRole('button', { name: /duplicate plan/i }));

      await waitFor(() => {
        expect(mockPlansApi.duplicate).toHaveBeenCalledWith(
          mockPlan.id,
          expect.any(String) // date string
        );
      });
    });

    it('should close dialog after successful duplication', async () => {
      const user = userEvent.setup();
      const duplicatedPlan = createMealPlan({
        id: 'new-plan-id',
        start_date: '2025-01-22',
        end_date: '2025-01-24',
        meals: mockPlan.meals,
      });

      mockPlansApi.list.mockResolvedValue(mockAxiosResponse([mockPlan]));
      mockPlansApi.duplicate.mockResolvedValue(mockAxiosResponse(duplicatedPlan));

      renderWithQuery(<PlanView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /duplicate meal plan/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /duplicate plan/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });
});
