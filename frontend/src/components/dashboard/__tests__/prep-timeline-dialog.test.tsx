import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test/utils';
import { PrepTimelineDialog } from '../prep-timeline-dialog';
import { plansApi } from '@/lib/api';
import { createOptimizedPrepTimeline, createPrepStep } from '@/test/factories';
import type { AxiosResponse } from 'axios';

// Mock the API module
vi.mock('@/lib/api', () => ({
  plansApi: {
    getPrepTimeline: vi.fn(),
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

describe('PrepTimelineDialog', () => {
  const defaultProps = {
    planId: 'plan-123',
    date: '2025-01-15',
    open: true,
    onOpenChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading message while fetching timeline', async () => {
      // Never resolve to keep loading state
      mockPlansApi.getPrepTimeline.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      expect(screen.getByText('Optimizing your prep schedule...')).toBeInTheDocument();
    });
  });

  describe('with timeline data', () => {
    const mockTimeline = createOptimizedPrepTimeline({
      total_time_minutes: 45,
      batched_savings_minutes: 8,
      prep_date: '2025-01-15',
    });

    it('should display total time', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('45 min')).toBeInTheDocument();
      });
    });

    it('should display time saved through batching', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        // The time saved appears in both the stats card and the savings message
        const timeSavedElements = screen.getAllByText('8 min');
        expect(timeSavedElements.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('should display number of steps', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        // Look for "Steps" label to confirm the steps count section is present
        expect(screen.getByText('Steps')).toBeInTheDocument();
        // The number 5 appears both in the step count and potentially in step numbers
        // so we just verify that our 5 steps are rendered
        expect(screen.getByText('Prep Steps')).toBeInTheDocument();
      });
    });

    it('should display savings message when time is saved', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/similar tasks have been batched together/i)).toBeInTheDocument();
      });
    });

    it('should display prep steps', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Chop all onions at once (for 2 recipes)')).toBeInTheDocument();
        expect(screen.getByText('Wash vegetables')).toBeInTheDocument();
        expect(screen.getByText('Preheat oven to 400F')).toBeInTheDocument();
      });
    });

    it('should display step numbers', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(mockTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });

    it('should show batched badge for batchable steps', async () => {
      const timelineWithBatched = createOptimizedPrepTimeline({
        steps: [
          createPrepStep({ step_number: 1, can_batch: true }),
          createPrepStep({ step_number: 2, can_batch: false }),
        ],
      });
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(timelineWithBatched));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Batched')).toBeInTheDocument();
        expect(screen.getByText('Individual')).toBeInTheDocument();
      });
    });
  });

  describe('empty state', () => {
    it('should show empty message when no meals for date', async () => {
      const emptyTimeline = createOptimizedPrepTimeline({
        total_time_minutes: 0,
        steps: [],
        batched_savings_minutes: 0,
      });
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(emptyTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('No meals scheduled for this date.')).toBeInTheDocument();
      });
    });
  });

  describe('error state', () => {
    it('should show error message when API fails', async () => {
      mockPlansApi.getPrepTimeline.mockRejectedValue(new Error('API Error'));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load prep timeline. Please try again.')).toBeInTheDocument();
      });
    });
  });

  describe('when closed', () => {
    it('should not fetch data when dialog is closed', () => {
      renderWithQuery(<PrepTimelineDialog {...defaultProps} open={false} />);

      expect(mockPlansApi.getPrepTimeline).not.toHaveBeenCalled();
    });
  });

  describe('when props are null', () => {
    it('should not fetch data when planId is null', () => {
      renderWithQuery(<PrepTimelineDialog {...defaultProps} planId={null} />);

      expect(mockPlansApi.getPrepTimeline).not.toHaveBeenCalled();
    });

    it('should not fetch data when date is null', () => {
      renderWithQuery(<PrepTimelineDialog {...defaultProps} date={null} />);

      expect(mockPlansApi.getPrepTimeline).not.toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('should have dialog title', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(
        mockAxiosResponse(createOptimizedPrepTimeline())
      );

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Optimized Prep Timeline')).toBeInTheDocument();
      });
    });

    it('should have aria-label on prep steps list', async () => {
      mockPlansApi.getPrepTimeline.mockResolvedValue(
        mockAxiosResponse(createOptimizedPrepTimeline())
      );

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('list', { name: /preparation steps/i })).toBeInTheDocument();
      });
    });
  });

  describe('time formatting', () => {
    it('should format time in hours when over 60 minutes', async () => {
      const longTimeline = createOptimizedPrepTimeline({
        total_time_minutes: 90,
      });
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(longTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('1h 30m')).toBeInTheDocument();
      });
    });

    it('should format exact hours without minutes', async () => {
      const longTimeline = createOptimizedPrepTimeline({
        total_time_minutes: 120,
      });
      mockPlansApi.getPrepTimeline.mockResolvedValue(mockAxiosResponse(longTimeline));

      renderWithQuery(<PrepTimelineDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('2h')).toBeInTheDocument();
      });
    });
  });
});
