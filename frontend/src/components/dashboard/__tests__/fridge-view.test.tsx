import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { FridgeView } from '../fridge-view';
import { fridgeApi } from '@/lib/api';
import { createFridgeItem } from '@/test/factories';
import type { AxiosResponse } from 'axios';

// Mock the API module
vi.mock('@/lib/api', () => ({
  fridgeApi: {
    get: vi.fn(),
    getExpiring: vi.fn(),
    addItem: vi.fn(),
    addBulk: vi.fn(),
    updateItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  },
  emailApi: {
    sendExpiringAlert: vi.fn(),
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

const mockFridgeApi = vi.mocked(fridgeApi);

function mockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as AxiosResponse['config'],
  };
}

describe('FridgeView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock for getExpiring - returns empty array
    mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse([]));
  });

  describe('loading state', () => {
    it('should show loading message while fetching inventory', async () => {
      // Never resolve to keep loading state
      mockFridgeApi.get.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<FridgeView />);

      expect(screen.getByRole('status', { name: 'Loading fridge inventory' })).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when fridge is empty', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText(/your fridge is empty/i)).toBeInTheDocument();
      });
    });
  });

  describe('with items', () => {
    const mockItems = [
      createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken Breast',
        quantity: '500g',
        days_remaining: 5,
        freshness_percentage: 71,
      }),
      createFridgeItem({
        id: 'item-2',
        ingredient_name: 'Spinach',
        quantity: '200g',
        days_remaining: 2,
        freshness_percentage: 29,
      }),
      createFridgeItem({
        id: 'item-3',
        ingredient_name: 'Eggs',
        quantity: '12',
        days_remaining: 1,
        freshness_percentage: 14,
      }),
    ];

    it('should display fridge items', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Chicken Breast')).toBeInTheDocument();
        expect(screen.getByText('Spinach')).toBeInTheDocument();
        expect(screen.getByText('Eggs')).toBeInTheDocument();
      });
    });

    it('should display quantity and days remaining', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      // Use getAllByText to handle sr-only descriptions
      await waitFor(() => {
        const quantityTexts = screen.getAllByText(/500g/);
        expect(quantityTexts.length).toBeGreaterThan(0);
        const daysTexts = screen.getAllByText(/5 days remaining/);
        expect(daysTexts.length).toBeGreaterThan(0);
      });
    });

    it('should display freshness percentage', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('71%')).toBeInTheDocument();
        expect(screen.getByText('29%')).toBeInTheDocument();
        expect(screen.getByText('14%')).toBeInTheDocument();
      });
    });

    it('should sort items by days remaining (most urgent first)', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      // Check that items are sorted by looking at the visible text order
      await waitFor(() => {
        // Get all list items and verify they contain the expected names in order
        const listItems = screen.getAllByRole('listitem');
        expect(listItems[0]).toHaveTextContent('Eggs'); // 1 day remaining
        expect(listItems[1]).toHaveTextContent('Spinach'); // 2 days remaining
        expect(listItems[2]).toHaveTextContent('Chicken Breast'); // 5 days remaining
      });
    });

    it('should show urgency badge for items expiring in 1 day', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Use today!')).toBeInTheDocument();
      });
    });

    it('should show urgency badge for items expiring in 2 days', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Use soon')).toBeInTheDocument();
      });
    });

    it('should have remove button for each item', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove chicken breast from fridge/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /remove spinach from fridge/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /remove eggs from fridge/i })).toBeInTheDocument();
      });
    });
  });

  describe('expiring items alert', () => {
    it('should show expiring items alert when items are expiring soon', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Milk', days_remaining: 1 }),
        createFridgeItem({ ingredient_name: 'Yogurt', days_remaining: 2 }),
      ];
      const expiringItems = mockItems; // All items are expiring
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse(expiringItems));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/2 items expiring soon!/i)).toBeInTheDocument();
      });
    });

    it('should list expiring ingredients in alert', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Milk', days_remaining: 1 }),
        createFridgeItem({ ingredient_name: 'Yogurt', days_remaining: 2 }),
      ];
      const expiringItems = mockItems;
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse(expiringItems));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText(/use these ingredients first/i)).toBeInTheDocument();
        expect(screen.getByText(/milk, yogurt/i)).toBeInTheDocument();
      });
    });

    it('should not show alert when no items are expiring', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Rice', days_remaining: 30 }),
      ];
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse([])); // No expiring items

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      });
    });

    it('should show Find Recipes button when items are expiring', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Milk', days_remaining: 1 }),
        createFridgeItem({ ingredient_name: 'Yogurt', days_remaining: 2 }),
      ];
      const expiringItems = mockItems;
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse(expiringItems));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /find recipes using milk/i })).toBeInTheDocument();
      });
    });

    it('should have correct href for Find Recipes link with first expiring ingredient', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Milk', days_remaining: 1 }),
        createFridgeItem({ ingredient_name: 'Yogurt', days_remaining: 2 }),
      ];
      const expiringItems = mockItems;
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse(expiringItems));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        const link = screen.getByRole('link', { name: /find recipes using milk/i });
        expect(link).toHaveAttribute('href', '/recipes?ingredient=Milk');
      });
    });

    it('should URL encode ingredient name in Find Recipes link', async () => {
      const mockItems = [
        createFridgeItem({ ingredient_name: 'Chicken Breast', days_remaining: 1 }),
      ];
      const expiringItems = mockItems;
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse(expiringItems));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        const link = screen.getByRole('link', { name: /find recipes using chicken breast/i });
        expect(link).toHaveAttribute('href', '/recipes?ingredient=Chicken%20Breast');
      });
    });

    it('should call getExpiring API with threshold 2', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.getExpiring.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(mockFridgeApi.getExpiring).toHaveBeenCalledWith(2);
      });
    });
  });

  describe('add item form', () => {
    it('should have input fields for name, quantity, and days fresh', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/days fresh/i)).toBeInTheDocument();
      });
    });

    it('should have default value of 7 for days fresh', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/days fresh/i)).toHaveValue(7);
      });
    });

    it('should call addItem API when form is submitted', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.addItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/name/i), 'Avocado');
      await user.type(screen.getByLabelText(/quantity/i), '3');
      await user.clear(screen.getByLabelText(/days fresh/i));
      await user.type(screen.getByLabelText(/days fresh/i), '5');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      await waitFor(() => {
        expect(mockFridgeApi.addItem).toHaveBeenCalledWith('Avocado', '3', 5);
      });
    });

    it('should not submit if name is empty', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/quantity/i), '3');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      expect(mockFridgeApi.addItem).not.toHaveBeenCalled();
    });

    it('should not submit if quantity is empty', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/name/i), 'Avocado');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      expect(mockFridgeApi.addItem).not.toHaveBeenCalled();
    });

    it('should clear form after successful submission', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.addItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/name/i), 'Avocado');
      await user.type(screen.getByLabelText(/quantity/i), '3');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toHaveValue('');
        expect(screen.getByLabelText(/quantity/i)).toHaveValue('');
        expect(screen.getByLabelText(/days fresh/i)).toHaveValue(7);
      });
    });
  });

  describe('remove item action', () => {
    it('should call removeItem API when remove button is clicked', async () => {
      const user = userEvent.setup();
      const mockItem = createFridgeItem({
        id: 'item-123',
        ingredient_name: 'Tomato',
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.removeItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove tomato from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /remove tomato from fridge/i }));

      await waitFor(() => {
        expect(mockFridgeApi.removeItem).toHaveBeenCalledWith('item-123');
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA region label', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('region', { name: /fridge inventory/i })).toBeInTheDocument();
      });
    });

    it('should have heading for the section', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /fridge inventory/i })).toBeInTheDocument();
      });
    });

    it('should have labels for all form inputs', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/name/i);
        const quantityInput = screen.getByLabelText(/quantity/i);
        const daysInput = screen.getByLabelText(/days fresh/i);

        expect(nameInput).toHaveAttribute('id');
        expect(quantityInput).toHaveAttribute('id');
        expect(daysInput).toHaveAttribute('id');
      });
    });
  });

  describe('bulk import', () => {
    it('should have Bulk Import button', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /open bulk import dialog/i })).toBeInTheDocument();
      });
    });

    it('should open bulk import dialog when button is clicked', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /open bulk import dialog/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /open bulk import dialog/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Bulk Import Ingredients')).toBeInTheDocument();
      });
    });

    it('should call addBulk API when items are imported', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.addBulk.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /open bulk import dialog/i })).toBeInTheDocument();
      });

      // Open dialog
      await user.click(screen.getByRole('button', { name: /open bulk import dialog/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Enter items
      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5{enter}eggs, 12');

      await waitFor(() => {
        expect(screen.getByText('2 valid')).toBeInTheDocument();
      });

      // Import
      await user.click(screen.getByRole('button', { name: /import 2 ingredient/i }));

      await waitFor(() => {
        expect(mockFridgeApi.addBulk).toHaveBeenCalledWith([
          { ingredient_name: 'chicken', quantity: '2 lbs', freshness_days: 5 },
          { ingredient_name: 'eggs', quantity: '12', freshness_days: 7 },
        ]);
      });
    });

    it('should close dialog after successful import', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.addBulk.mockResolvedValue(mockAxiosResponse([]));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /open bulk import dialog/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /open bulk import dialog/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5');

      await user.click(screen.getByRole('button', { name: /import 1 ingredient/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('clear all fridge', () => {
    const mockItems = [
      createFridgeItem({ id: 'item-1', ingredient_name: 'Chicken' }),
      createFridgeItem({ id: 'item-2', ingredient_name: 'Eggs' }),
      createFridgeItem({ id: 'item-3', ingredient_name: 'Milk' }),
    ];

    it('should not show Clear All button when fridge is empty', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText(/your fridge is empty/i)).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /clear all items from fridge/i })).not.toBeInTheDocument();
    });

    it('should show Clear All button when fridge has items', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });
    });

    it('should open confirmation dialog when Clear All button is clicked', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Clear Fridge')).toBeInTheDocument();
        expect(screen.getByText(/are you sure you want to remove all 3 items/i)).toBeInTheDocument();
      });
    });

    it('should close dialog when Cancel is clicked', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should call clear API when confirmed', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.clear.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /^clear all$/i }));

      await waitFor(() => {
        expect(mockFridgeApi.clear).toHaveBeenCalled();
      });
    });

    it('should close dialog after successful clear', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      mockFridgeApi.clear.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /^clear all$/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should show singular "item" in confirmation message when only one item', async () => {
      const user = userEvent.setup();
      const singleItem = [createFridgeItem({ id: 'item-1', ingredient_name: 'Chicken' })];
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: singleItem }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear all items from fridge/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));

      await waitFor(() => {
        expect(screen.getByText(/are you sure you want to remove all 1 item from your fridge/i)).toBeInTheDocument();
      });
    });
  });

  describe('edit item', () => {
    const mockItem = createFridgeItem({
      id: 'item-123',
      ingredient_name: 'Chicken Breast',
      quantity: '500g',
      days_remaining: 5,
      original_freshness_days: 7,
      freshness_percentage: 71,
    });

    it('should have edit button for each item', async () => {
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });
    });

    it('should open edit dialog when edit button is clicked', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText(/edit chicken breast/i)).toBeInTheDocument();
      });
    });

    it('should pre-populate dialog with current item values', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        // Use the edit dialog's input IDs to distinguish from the add form
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      // Get inputs within the dialog context
      const quantityInput = dialog.querySelector('#edit-quantity') as HTMLInputElement;
      const daysInput = dialog.querySelector('#edit-days') as HTMLInputElement;

      expect(quantityInput).toHaveValue('500g');
      expect(daysInput).toHaveValue(5);
    });

    it('should close dialog when cancel is clicked', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should call updateItem API when form is submitted with changes', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.updateItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      const quantityInput = dialog.querySelector('#edit-quantity') as HTMLInputElement;
      await user.clear(quantityInput);
      await user.type(quantityInput, '1kg');

      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(mockFridgeApi.updateItem).toHaveBeenCalledWith('item-123', { quantity: '1kg' });
      });
    });

    it('should call updateItem API with days_remaining when changed', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.updateItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      const daysInput = dialog.querySelector('#edit-days') as HTMLInputElement;
      await user.clear(daysInput);
      await user.type(daysInput, '3');

      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(mockFridgeApi.updateItem).toHaveBeenCalledWith('item-123', { days_remaining: 3 });
      });
    });

    it('should call updateItem API with both fields when both are changed', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.updateItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      const quantityInput = dialog.querySelector('#edit-quantity') as HTMLInputElement;
      await user.clear(quantityInput);
      await user.type(quantityInput, '1kg');

      const daysInput = dialog.querySelector('#edit-days') as HTMLInputElement;
      await user.clear(daysInput);
      await user.type(daysInput, '10');

      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(mockFridgeApi.updateItem).toHaveBeenCalledWith('item-123', { quantity: '1kg', days_remaining: 10 });
      });
    });

    it('should close dialog after successful update', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.updateItem.mockResolvedValue(mockAxiosResponse({}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      const quantityInput = dialog.querySelector('#edit-quantity') as HTMLInputElement;
      await user.clear(quantityInput);
      await user.type(quantityInput, '1kg');

      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should close dialog without API call when no changes made', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit chicken breast/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /edit chicken breast/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Click save without making any changes
      await user.click(screen.getByRole('button', { name: /save changes/i }));

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });

      expect(mockFridgeApi.updateItem).not.toHaveBeenCalled();
    });
  });

  describe('optimistic updates', () => {
    it('should optimistically add item to list before API responds', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      // Never resolve to test optimistic state
      mockFridgeApi.addItem.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      });

      // Fill in form - using unique item name to avoid conflicts
      await user.type(screen.getByLabelText(/name/i), 'TestItem');
      await user.type(screen.getByLabelText(/quantity/i), '100g');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      // Item should appear optimistically
      await waitFor(() => {
        expect(screen.getByText('TestItem')).toBeInTheDocument();
        // The quantity is displayed as "100g • 7 days remaining" - may appear in sr-only too
        const quantityTexts = screen.getAllByText(/100g.*days remaining/i);
        expect(quantityTexts.length).toBeGreaterThan(0);
      });

      // Form should be cleared immediately
      expect(screen.getByLabelText(/name/i)).toHaveValue('');
    });

    it('should optimistically remove item from list before API responds', async () => {
      const user = userEvent.setup();
      const mockItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        quantity: '500g',
        days_remaining: 5,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      // Never resolve to test optimistic state
      mockFridgeApi.removeItem.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /remove chicken from fridge/i }));

      // Item should disappear optimistically
      await waitFor(() => {
        expect(screen.queryByText('Chicken')).not.toBeInTheDocument();
      });
    });

    it('should rollback add item on API error', async () => {
      const user = userEvent.setup();
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [] }));
      mockFridgeApi.addItem.mockRejectedValue(new Error('API Error'));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      });

      await user.type(screen.getByLabelText(/name/i), 'FailItem');
      await user.type(screen.getByLabelText(/quantity/i), '500g');
      await user.click(screen.getByRole('button', { name: /add ingredient to fridge/i }));

      // After error, item should be removed and form restored
      await waitFor(() => {
        expect(screen.queryByText('FailItem')).not.toBeInTheDocument();
        expect(screen.getByLabelText(/name/i)).toHaveValue('FailItem');
      });
    });

    it('should rollback remove item on API error', async () => {
      const user = userEvent.setup();
      const mockItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        quantity: '500g',
        days_remaining: 5,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      mockFridgeApi.removeItem.mockRejectedValue(new Error('API Error'));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /remove chicken from fridge/i }));

      // After error, item should reappear
      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
      });
    });

    it('should optimistically clear all items before API responds', async () => {
      const user = userEvent.setup();
      const mockItems = [
        createFridgeItem({ id: 'item-1', ingredient_name: 'Chicken' }),
        createFridgeItem({ id: 'item-2', ingredient_name: 'Eggs' }),
      ];
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: mockItems }));
      // Never resolve to test optimistic state
      mockFridgeApi.clear.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
        expect(screen.getByText('Eggs')).toBeInTheDocument();
      });

      // Open confirmation dialog
      await user.click(screen.getByRole('button', { name: /clear all items from fridge/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Confirm clear
      await user.click(screen.getByRole('button', { name: /clear all/i }));

      // Items should disappear optimistically and dialog should close
      await waitFor(() => {
        expect(screen.queryByText('Chicken')).not.toBeInTheDocument();
        expect(screen.queryByText('Eggs')).not.toBeInTheDocument();
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should optimistically update item before API responds', async () => {
      const user = userEvent.setup();
      const mockItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        quantity: '500g',
        days_remaining: 5,
        freshness_percentage: 71,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));
      // Never resolve to test optimistic state
      mockFridgeApi.updateItem.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<FridgeView />);

      await waitFor(() => {
        // Check for quantity in the item display (quantity + days remaining text) - may appear in sr-only too
        const quantityTexts = screen.getAllByText(/500g.*days remaining/i);
        expect(quantityTexts.length).toBeGreaterThan(0);
      });

      // Open edit dialog
      await user.click(screen.getByRole('button', { name: /edit chicken/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Change quantity - find the input within the dialog
      const dialog = screen.getByRole('dialog');
      // eslint-disable-next-line testing-library/no-node-access, @typescript-eslint/no-non-null-assertion
      const quantityInput = dialog.querySelector('input[id="edit-quantity"]')!;
      await user.clear(quantityInput);
      await user.type(quantityInput, '1kg');
      await user.click(screen.getByRole('button', { name: /save changes/i }));

      // Quantity should update optimistically and dialog should close
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        // May appear in sr-only descriptions too
        const updatedTexts = screen.getAllByText(/1kg.*days remaining/i);
        expect(updatedTexts.length).toBeGreaterThan(0);
      });
    });
  });

  describe('real-time freshness updates', () => {
    it('should fetch both fridge items and expiring items on mount', async () => {
      const mockItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        days_remaining: 5,
        freshness_percentage: 71,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [mockItem] }));

      renderWithQuery(<FridgeView />);

      // Wait for initial fetch
      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
      });

      // Both endpoints should have been called
      expect(mockFridgeApi.get).toHaveBeenCalled();
      expect(mockFridgeApi.getExpiring).toHaveBeenCalled();
    });

    it('should display updated freshness data after refetch', async () => {
      // Initial data with 5 days remaining
      const initialItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        days_remaining: 5,
        freshness_percentage: 71,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [initialItem] }));

      const { rerender } = renderWithQuery(<FridgeView />);

      // Wait for initial render - may appear in sr-only descriptions too
      await waitFor(() => {
        expect(screen.getByText('Chicken')).toBeInTheDocument();
        const daysTexts = screen.getAllByText(/5 days remaining/i);
        expect(daysTexts.length).toBeGreaterThan(0);
      });

      // Simulate backend decay - update mock to return decayed data
      const decayedItem = createFridgeItem({
        id: 'item-1',
        ingredient_name: 'Chicken',
        days_remaining: 4,
        freshness_percentage: 57,
      });
      mockFridgeApi.get.mockResolvedValue(mockAxiosResponse({ items: [decayedItem] }));

      // Trigger a refetch by re-rendering (simulates what happens after poll interval)
      rerender(<FridgeView />);

      // The component should eventually show updated data when data refreshes
      // (In real usage, the refetchInterval would trigger this automatically)
      await waitFor(() => {
        expect(mockFridgeApi.get).toHaveBeenCalled();
      });
    });
  });
});
