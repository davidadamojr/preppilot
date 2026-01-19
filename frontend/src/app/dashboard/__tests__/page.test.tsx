import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test/utils';
import DashboardPage from '../page';
import { createUser } from '@/test/factories';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

// Create a mutable mock user that tests can modify
const mockUser = createUser({
  email: 'test@example.com',
  full_name: null,
  diet_type: 'low_histamine',
  dietary_exclusions: ['dairy', 'gluten'],
  is_active: true,
  created_at: '2024-01-15T10:00:00Z',
});

// Track loading state
let mockIsLoading = false;

// Mock the auth context
vi.mock('@/lib/auth-context', () => ({
  useAuth: () => ({
    user: mockIsLoading ? null : mockUser,
    isLoading: mockIsLoading,
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the dashboard components to simplify tests
vi.mock('@/components/dashboard/plan-view', () => ({
  PlanView: () => <div data-testid="plan-view">Plan View</div>,
}));

vi.mock('@/components/dashboard/fridge-view', () => ({
  FridgeView: () => <div data-testid="fridge-view">Fridge View</div>,
}));

vi.mock('@/components/dashboard/catch-up-view', () => ({
  CatchUpView: () => <div data-testid="catch-up-view">Catch Up View</div>,
}));

vi.mock('@/components/dashboard/settings-view', () => ({
  SettingsView: () => <div data-testid="settings-view">Settings View</div>,
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsLoading = false;
    // Reset user to default state
    mockUser.email = 'test@example.com';
    mockUser.full_name = null;
    mockUser.diet_type = 'low_histamine';
    mockUser.dietary_exclusions = ['dairy', 'gluten'];
    mockUser.is_active = true;
  });

  describe('header display', () => {
    it('should display the PrepPilot title', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('PrepPilot')).toBeInTheDocument();
      });
    });

    it('should display user email', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
      });
    });

    it('should display full_name when set', async () => {
      mockUser.full_name = 'John Doe';

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        // Email should still be displayed
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
      });
    });

    it('should not display full_name element when null', async () => {
      mockUser.full_name = null;

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
      });

      // Should not have any element with a name that looks like a full name
      // The email should be the only user identifier shown
      const userInfoSection = screen.getByText('test@example.com').parentElement;
      expect(userInfoSection?.children.length).toBe(1);
    });

    it('should display both full_name and email with proper styling', async () => {
      mockUser.full_name = 'Jane Smith';

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        const nameElement = screen.getByText('Jane Smith');
        const emailElement = screen.getByText('test@example.com');

        // Name should have font-medium class for emphasis
        expect(nameElement.className).toContain('font-medium');
        // Email should have gray color for secondary importance
        expect(emailElement.className).toContain('text-gray-600');
      });
    });

    it('should display diet type badge with proper label', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Low Histamine')).toBeInTheDocument();
      });
    });

    it('should display Low FODMAP diet type', async () => {
      mockUser.diet_type = 'fodmap';

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Low FODMAP')).toBeInTheDocument();
      });
    });

    it('should display Fructose Free diet type', async () => {
      mockUser.diet_type = 'fructose_free';

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Fructose Free')).toBeInTheDocument();
      });
    });

    it('should display raw diet type if label not found', async () => {
      // Use type assertion to test fallback for unknown diet types
      // This simulates a scenario where backend returns an unexpected value
      (mockUser as { diet_type: string }).diet_type = 'custom_diet';

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('custom_diet')).toBeInTheDocument();
      });

      // Reset to valid type
      mockUser.diet_type = 'low_histamine';
    });

    it('should display dietary exclusions count (plural)', async () => {
      mockUser.dietary_exclusions = ['dairy', 'gluten'];

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('2 exclusions')).toBeInTheDocument();
      });
    });

    it('should display dietary exclusions count (singular)', async () => {
      mockUser.dietary_exclusions = ['dairy'];

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('1 exclusion')).toBeInTheDocument();
      });
    });

    it('should not display exclusions badge when no exclusions', async () => {
      mockUser.dietary_exclusions = [];

      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Low Histamine')).toBeInTheDocument();
      });

      expect(screen.queryByText(/exclusion/i)).not.toBeInTheDocument();
    });

    it('should display Browse Recipes link', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /browse recipes/i })).toBeInTheDocument();
      });
    });

    it('should display Sign out button', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
      });
    });
  });

  describe('tabs', () => {
    it('should display all four tabs', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /plan/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /fridge/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /catch-up/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /settings/i })).toBeInTheDocument();
      });
    });

    it('should show Plan tab as default active', async () => {
      renderWithQuery(<DashboardPage />);

      await waitFor(() => {
        expect(screen.getByTestId('plan-view')).toBeInTheDocument();
      });
    });
  });

  describe('loading state', () => {
    it('should show loading state while checking auth', async () => {
      mockIsLoading = true;

      renderWithQuery(<DashboardPage />);

      expect(screen.getByRole('status', { name: 'Loading dashboard' })).toBeInTheDocument();
    });
  });
});
