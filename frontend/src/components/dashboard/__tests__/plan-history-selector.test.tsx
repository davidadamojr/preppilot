import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { PlanHistorySelector } from '../plan-history-selector';
import { createMealPlan } from '@/test/factories';

// Helper to format date as displayed in the component
// Parse as local time to match the component behavior
const formatDateRange = (startDate: string, endDate: string) => {
  const [startYear, startMonth, startDay] = startDate.split('-').map(Number);
  const [endYear, endMonth, endDay] = endDate.split('-').map(Number);
  const start = new Date(startYear, startMonth - 1, startDay);
  const end = new Date(endYear, endMonth - 1, endDay);
  const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  return `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
};

// Fixed dates for testing
const PLAN_1_START = '2025-01-15';
const PLAN_1_END = '2025-01-17';
const PLAN_2_START = '2025-01-10';
const PLAN_2_END = '2025-01-12';
const PLAN_3_START = '2025-01-05';
const PLAN_3_END = '2025-01-07';

describe('PlanHistorySelector', () => {
  const mockOnSelectPlan = vi.fn();
  const mockOnLoadMore = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should not render when there is only one plan', () => {
      const singlePlan = [createMealPlan({ id: 'plan-1' })];

      const { container } = renderWithQuery(
        <PlanHistorySelector
          plans={singlePlan}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render when there are multiple plans', () => {
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      expect(screen.getByRole('button', { name: /select meal plan/i })).toBeInTheDocument();
    });

    it('should display the selected plan date range in the trigger', () => {
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      const trigger = screen.getByRole('button', { name: /select meal plan/i });
      const expectedDateRange = formatDateRange(PLAN_1_START, PLAN_1_END);
      expect(trigger).toHaveTextContent(expectedDateRange);
    });
  });

  describe('dropdown behavior', () => {
    it('should open dropdown when trigger is clicked', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText('Plan History')).toBeInTheDocument();
      });
    });

    it('should display all plans in the dropdown', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
        createMealPlan({ id: 'plan-3', start_date: PLAN_3_START, end_date: PLAN_3_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        // Use getAllByText since the selected plan appears both in trigger and dropdown
        const plan1Elements = screen.getAllByText(formatDateRange(PLAN_1_START, PLAN_1_END));
        expect(plan1Elements.length).toBeGreaterThanOrEqual(1);
        // Other plans should appear in dropdown only
        expect(screen.getByText(formatDateRange(PLAN_2_START, PLAN_2_END))).toBeInTheDocument();
        expect(screen.getByText(formatDateRange(PLAN_3_START, PLAN_3_END))).toBeInTheDocument();
      });
    });

    it('should show "Latest" badge for the first plan', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText('Latest')).toBeInTheDocument();
      });
    });
  });

  describe('plan selection', () => {
    it('should call onSelectPlan when a plan is clicked', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      const plan2DateRange = formatDateRange(PLAN_2_START, PLAN_2_END);
      await waitFor(() => {
        expect(screen.getByText(plan2DateRange)).toBeInTheDocument();
      });

      // Click on the second plan
      await user.click(screen.getByText(plan2DateRange));

      expect(mockOnSelectPlan).toHaveBeenCalledWith('plan-2');
    });

    it('should show checkmark for the selected plan', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        // Find menu items to verify the selected plan has a checkmark
        const menuItems = screen.getAllByRole('menuitem');
        expect(menuItems.length).toBe(2);
        // The first menu item (selected plan) should have a check icon SVG
        const firstMenuItem = menuItems[0];
        const checkSvg = firstMenuItem.querySelector('svg.lucide-check');
        expect(checkSvg).toBeInTheDocument();
      });
    });
  });

  describe('load more functionality', () => {
    it('should show "Load More Plans" button when hasMore is true', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={true}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /load more plans/i })).toBeInTheDocument();
      });
    });

    it('should not show "Load More Plans" button when hasMore is false', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText('Plan History')).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /load more plans/i })).not.toBeInTheDocument();
    });

    it('should call onLoadMore when "Load More Plans" button is clicked', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={true}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /load more plans/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /load more plans/i }));

      expect(mockOnLoadMore).toHaveBeenCalled();
    });

    it('should show "Loading..." text when isLoadingMore is true', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={true}
          isLoadingMore={true}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText('Loading...')).toBeInTheDocument();
      });
    });

    it('should disable "Load More Plans" button when loading', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={true}
          isLoadingMore={true}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        const loadMoreButton = screen.getByText('Loading...');
        expect(loadMoreButton.closest('button')).toBeDisabled();
      });
    });
  });

  describe('plan metadata display', () => {
    it('should display diet type for each plan', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END, diet_type: 'low_histamine' }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END, diet_type: 'fodmap' }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        expect(screen.getByText(/low_histamine/)).toBeInTheDocument();
        expect(screen.getByText(/fodmap/)).toBeInTheDocument();
      });
    });

    it('should display meal count for each plan', async () => {
      const user = userEvent.setup();
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }), // default has 3 meals
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      await user.click(screen.getByRole('button', { name: /select meal plan/i }));

      await waitFor(() => {
        // Each plan shows "X meals" - default factory creates 3 meals
        const mealCountElements = screen.getAllByText(/3 meals/);
        expect(mealCountElements.length).toBe(2);
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper aria-label on trigger button', () => {
      const plans = [
        createMealPlan({ id: 'plan-1', start_date: PLAN_1_START, end_date: PLAN_1_END }),
        createMealPlan({ id: 'plan-2', start_date: PLAN_2_START, end_date: PLAN_2_END }),
      ];

      renderWithQuery(
        <PlanHistorySelector
          plans={plans}
          selectedPlanId="plan-1"
          onSelectPlan={mockOnSelectPlan}
          onLoadMore={mockOnLoadMore}
          hasMore={false}
          isLoadingMore={false}
        />
      );

      expect(screen.getByRole('button', { name: /select meal plan/i })).toBeInTheDocument();
    });
  });
});
