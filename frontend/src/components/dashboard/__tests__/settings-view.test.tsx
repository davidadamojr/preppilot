import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { SettingsView } from '../settings-view';
import { authApi } from '@/lib/api';
import { createUser } from '@/test/factories';
import type { AxiosResponse } from 'axios';

// Mock the auth context
const mockUpdateExclusions = vi.fn();
const mockLogout = vi.fn();
const mockRefreshProfile = vi.fn();
const mockUser = createUser({
  email: 'user@example.com',
  diet_type: 'low_histamine',
  dietary_exclusions: [],
  is_active: true,
  created_at: '2024-01-15T10:00:00Z',
});

vi.mock('@/lib/auth-context', () => ({
  useAuth: () => ({
    user: mockUser,
    updateExclusions: mockUpdateExclusions,
    logout: mockLogout,
    refreshProfile: mockRefreshProfile,
  }),
}));

// Mock the API module
vi.mock('@/lib/api', () => ({
  authApi: {
    getAvailableExclusions: vi.fn(),
  },
}));

// Mock useToast hook
const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
    toasts: [],
    dismiss: vi.fn(),
  }),
}));

// Mock next/navigation
const mockRouterPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const mockAuthApi = vi.mocked(authApi);

function mockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as AxiosResponse['config'],
  };
}

const mockExclusions = [
  { name: 'Dairy', value: 'dairy' },
  { name: 'Gluten', value: 'gluten' },
  { name: 'Nuts', value: 'nuts' },
  { name: 'Eggs', value: 'eggs' },
  { name: 'Soy', value: 'soy' },
];

describe('SettingsView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset user to default state
    mockUser.email = 'user@example.com';
    mockUser.diet_type = 'low_histamine';
    mockUser.dietary_exclusions = [];
    mockUser.is_active = true;
    mockUser.created_at = '2024-01-15T10:00:00Z';
  });

  describe('profile display', () => {
    it('should display user email', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('user@example.com')).toBeInTheDocument();
      });
    });

    it('should display user diet type with proper label', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Low Histamine')).toBeInTheDocument();
      });
    });

    it('should display account status as Active badge', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
      });
    });

    it('should display member since date', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('January 15, 2024')).toBeInTheDocument();
      });
    });
  });

  describe('dietary exclusions', () => {
    it('should display available exclusion options', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
        expect(screen.getByText('Gluten')).toBeInTheDocument();
        expect(screen.getByText('Nuts')).toBeInTheDocument();
      });
    });

    it('should show current exclusions as checked', async () => {
      mockUser.dietary_exclusions = ['dairy', 'gluten'];
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        const dairyCheckbox = screen.getByRole('checkbox', { name: /dairy/i });
        const glutenCheckbox = screen.getByRole('checkbox', { name: /gluten/i });
        const nutsCheckbox = screen.getByRole('checkbox', { name: /nuts/i });

        expect(dairyCheckbox).toBeChecked();
        expect(glutenCheckbox).toBeChecked();
        expect(nutsCheckbox).not.toBeChecked();
      });
    });

    it('should toggle exclusion when checkbox is clicked', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      const dairyCheckbox = screen.getByRole('checkbox', { name: /dairy/i });
      expect(dairyCheckbox).not.toBeChecked();

      await user.click(dairyCheckbox);
      expect(dairyCheckbox).toBeChecked();

      await user.click(dairyCheckbox);
      expect(dairyCheckbox).not.toBeChecked();
    });

    it('should show selected exclusions as badges', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));
      await user.click(screen.getByRole('checkbox', { name: /nuts/i }));

      await waitFor(() => {
        expect(screen.getByText('Selected:')).toBeInTheDocument();
      });
    });
  });

  describe('save functionality', () => {
    it('should enable save button when exclusions change', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', { name: /save changes/i });
      expect(saveButton).toBeDisabled();

      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));

      await waitFor(() => {
        expect(saveButton).not.toBeDisabled();
      });
    });

    it('should show unsaved changes message when changes exist', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));

      await waitFor(() => {
        expect(screen.getByText('You have unsaved changes')).toBeInTheDocument();
      });
    });

    it('should call updateExclusions when save is clicked', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );
      mockUpdateExclusions.mockResolvedValue(undefined);

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));
      await user.click(screen.getByRole('checkbox', { name: /gluten/i }));
      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(mockUpdateExclusions).toHaveBeenCalledWith(['dairy', 'gluten']);
      });
    });

    it('should show success toast after saving', async () => {
      const user = userEvent.setup();
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );
      mockUpdateExclusions.mockResolvedValue(undefined);

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Dairy')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));
      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Settings saved',
          })
        );
      });
    });
  });

  describe('reset functionality', () => {
    it('should show reset button when changes exist', async () => {
      const user = userEvent.setup();
      mockUser.dietary_exclusions = ['dairy'];
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: /dairy/i })).toBeInTheDocument();
      });

      // Initially no reset button
      expect(screen.queryByRole('button', { name: /reset/i })).not.toBeInTheDocument();

      // Make a change
      await user.click(screen.getByRole('checkbox', { name: /gluten/i }));

      // Reset button should appear
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /reset/i })).toBeInTheDocument();
      });
    });

    it('should revert changes when reset is clicked', async () => {
      const user = userEvent.setup();
      mockUser.dietary_exclusions = ['dairy'];
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: /dairy/i })).toBeInTheDocument();
      });

      // Uncheck dairy and check gluten
      await user.click(screen.getByRole('checkbox', { name: /dairy/i }));
      await user.click(screen.getByRole('checkbox', { name: /gluten/i }));

      const dairyCheckbox = screen.getByRole('checkbox', { name: /dairy/i });
      const glutenCheckbox = screen.getByRole('checkbox', { name: /gluten/i });

      expect(dairyCheckbox).not.toBeChecked();
      expect(glutenCheckbox).toBeChecked();

      // Click reset
      await user.click(screen.getByRole('button', { name: /reset/i }));

      // Should revert to original state
      await waitFor(() => {
        expect(dairyCheckbox).toBeChecked();
        expect(glutenCheckbox).not.toBeChecked();
      });
    });
  });

  describe('loading state', () => {
    it('should show loading spinner while fetching exclusions', async () => {
      // Never resolve to keep loading state
      mockAuthApi.getAvailableExclusions.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<SettingsView />);

      // Profile card should be visible immediately
      expect(screen.getByText('Profile')).toBeInTheDocument();

      // Look for the loading skeleton for exclusions
      expect(screen.getByRole('status', { name: 'Loading dietary exclusions' })).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show message when no exclusion options available', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: [] })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('No exclusion options available')).toBeInTheDocument();
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper section titles', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        expect(screen.getByText('Profile')).toBeInTheDocument();
        expect(screen.getByText('Dietary Exclusions')).toBeInTheDocument();
      });
    });

    it('should have accessible checkbox labels', async () => {
      mockAuthApi.getAvailableExclusions.mockResolvedValue(
        mockAxiosResponse({ exclusions: mockExclusions })
      );

      renderWithQuery(<SettingsView />);

      await waitFor(() => {
        // Each checkbox should be labeled
        expect(screen.getByRole('checkbox', { name: /dairy/i })).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: /gluten/i })).toBeInTheDocument();
        expect(screen.getByRole('checkbox', { name: /nuts/i })).toBeInTheDocument();
      });
    });
  });
});
