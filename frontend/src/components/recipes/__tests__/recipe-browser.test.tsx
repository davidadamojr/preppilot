import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithQuery } from '@/test/utils';
import { RecipeBrowser } from '../recipe-browser';
import { recipesApi } from '@/lib/api';
import { createRecipe } from '@/test/factories';
import type { AxiosResponse } from 'axios';
import type { RecipeListResponse, RecipeSearchResponse } from '@/types';

// Mock the API module
vi.mock('@/lib/api', () => ({
  recipesApi: {
    list: vi.fn(),
    get: vi.fn(),
    searchByIngredient: vi.fn(),
  },
}));

// Mock useToast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
    toasts: [],
    dismiss: vi.fn(),
  }),
}));

const mockRecipesApi = vi.mocked(recipesApi);

function mockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as AxiosResponse['config'],
  };
}

function createRecipeListResponse(
  recipes: ReturnType<typeof createRecipe>[],
  total?: number,
  page = 1,
  pageSize = 12
): RecipeListResponse {
  return {
    recipes,
    total: total ?? recipes.length,
    page,
    page_size: pageSize,
  };
}

function createRecipeSearchResponse(
  ingredient: string,
  recipes: ReturnType<typeof createRecipe>[],
  total?: number,
  page = 1,
  pageSize = 12
): RecipeSearchResponse {
  return {
    ingredient,
    matching_recipes: recipes,
    count: recipes.length,
    total: total ?? recipes.length,
    page,
    page_size: pageSize,
  };
}

describe('RecipeBrowser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading message while fetching recipes', async () => {
      mockRecipesApi.list.mockImplementation(() => new Promise(() => {}));

      renderWithQuery(<RecipeBrowser />);

      expect(screen.getByRole('status', { name: 'Loading recipes' })).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no recipes found', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByText('No recipes found with the selected filters.')
        ).toBeInTheDocument();
      });
    });
  });

  describe('with recipes', () => {
    const mockRecipes = [
      createRecipe({
        id: 'recipe-1',
        name: 'Chicken Stir Fry',
        meal_type: 'dinner',
        prep_time_minutes: 25,
        diet_tags: ['high-protein', 'low-carb'],
        servings: 4,
      }),
      createRecipe({
        id: 'recipe-2',
        name: 'Veggie Omelette',
        meal_type: 'breakfast',
        prep_time_minutes: 15,
        diet_tags: ['vegetarian', 'gluten-free'],
        servings: 2,
      }),
      createRecipe({
        id: 'recipe-3',
        name: 'Quinoa Salad',
        meal_type: 'lunch',
        prep_time_minutes: 20,
        diet_tags: ['vegan', 'gluten-free', 'high-fiber'],
        servings: 3,
      }),
    ];

    it('should display recipe list', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(mockRecipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('Chicken Stir Fry')).toBeInTheDocument();
        expect(screen.getByText('Veggie Omelette')).toBeInTheDocument();
        expect(screen.getByText('Quinoa Salad')).toBeInTheDocument();
      });
    });

    it('should display prep time for each recipe', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(mockRecipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('25 min')).toBeInTheDocument();
        expect(screen.getByText('15 min')).toBeInTheDocument();
        expect(screen.getByText('20 min')).toBeInTheDocument();
      });
    });

    it('should display meal type for each recipe', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(mockRecipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('dinner')).toBeInTheDocument();
        expect(screen.getByText('breakfast')).toBeInTheDocument();
        expect(screen.getByText('lunch')).toBeInTheDocument();
      });
    });

    it('should display diet tags as badges', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(mockRecipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('high-protein')).toBeInTheDocument();
        expect(screen.getByText('vegetarian')).toBeInTheDocument();
        expect(screen.getByText('vegan')).toBeInTheDocument();
      });
    });

    it('should show +N badge when recipe has more than 3 diet tags', async () => {
      const recipeWithManyTags = createRecipe({
        diet_tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5'],
      });
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([recipeWithManyTags]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('+2')).toBeInTheDocument();
      });
    });

    it('should display ingredient and step counts', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(mockRecipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        // Default recipe has 2 ingredients and 2 steps
        const countTexts = screen.getAllByText(/2 ingredients/);
        expect(countTexts.length).toBeGreaterThan(0);
      });
    });
  });

  describe('filtering', () => {
    it('should have meal type filter dropdown', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByLabelText('Meal Type')).toBeInTheDocument();
      });
    });

    it('should have diet tag filter dropdown', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByLabelText('Diet Tag')).toBeInTheDocument();
      });
    });

    it('should call API with meal type filter when selected', async () => {
      const user = userEvent.setup();
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByLabelText('Meal Type')).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText('Meal Type'), 'dinner');

      await waitFor(() => {
        expect(mockRecipesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({ mealType: 'dinner' })
        );
      });
    });

    it('should call API with diet tag filter when selected', async () => {
      const user = userEvent.setup();
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByLabelText('Diet Tag')).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText('Diet Tag'), 'gluten-free');

      await waitFor(() => {
        expect(mockRecipesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({ dietTag: 'gluten-free' })
        );
      });
    });
  });

  describe('ingredient search', () => {
    it('should have search input field', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });
    });

    it('should search by ingredient when form is submitted', async () => {
      const user = userEvent.setup();
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', []))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'chicken'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        expect(mockRecipesApi.searchByIngredient).toHaveBeenCalledWith(
          'chicken',
          1,
          12
        );
      });
    });

    it('should show search results when searching', async () => {
      const user = userEvent.setup();
      const searchResults = [
        createRecipe({ name: 'Chicken Curry' }),
        createRecipe({ name: 'Grilled Chicken' }),
      ];
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', searchResults))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'chicken'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        expect(screen.getByText('Chicken Curry')).toBeInTheDocument();
        expect(screen.getByText('Grilled Chicken')).toBeInTheDocument();
      });
    });

    it('should show active search indicator when searching', async () => {
      const user = userEvent.setup();
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', [], 0))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'chicken'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/showing recipes containing:/i)
        ).toBeInTheDocument();
        expect(screen.getByText('chicken')).toBeInTheDocument();
      });
    });

    it('should show clear button when searching with results', async () => {
      const user = userEvent.setup();
      const searchResults = [createRecipe({ name: 'Chicken Dish' })];
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', searchResults))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'chicken'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        // The Clear button in the search form (with X icon)
        expect(screen.getByText('Clear')).toBeInTheDocument();
      });
    });

    it('should clear search and return to list when clear button is clicked', async () => {
      const user = userEvent.setup();
      const searchResults = [createRecipe({ name: 'Chicken Dish' })];
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', searchResults))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'chicken'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        expect(screen.getByText('Clear')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Clear'));

      await waitFor(() => {
        expect(
          screen.queryByText('Clear')
        ).not.toBeInTheDocument();
      });
    });

    it('should show empty state with clear link when no search results', async () => {
      const user = userEvent.setup();
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('xyz', []))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toBeInTheDocument();
      });

      await user.type(
        screen.getByPlaceholderText(/search by ingredient/i),
        'xyz'
      );
      await user.click(screen.getByRole('button', { name: /^search$/i }));

      await waitFor(() => {
        expect(
          screen.getByText('No recipes found containing "xyz"')
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument();
      });
    });
  });

  describe('pagination', () => {
    it('should show pagination when there are multiple pages', async () => {
      const recipes = Array.from({ length: 12 }, (_, i) =>
        createRecipe({ id: `recipe-${i}`, name: `Recipe ${i}` })
      );
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(recipes, 30, 1, 12))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
      });
    });

    it('should disable previous button on first page', async () => {
      const recipes = Array.from({ length: 12 }, (_, i) =>
        createRecipe({ id: `recipe-${i}`, name: `Recipe ${i}` })
      );
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(recipes, 30, 1, 12))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
      });
    });

    it('should call API with next page when next button is clicked', async () => {
      const user = userEvent.setup();
      const recipes = Array.from({ length: 12 }, (_, i) =>
        createRecipe({ id: `recipe-${i}`, name: `Recipe ${i}` })
      );
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(recipes, 30, 1, 12))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /next/i }));

      await waitFor(() => {
        expect(mockRecipesApi.list).toHaveBeenLastCalledWith(
          expect.objectContaining({ page: 2 })
        );
      });
    });

    it('should not show pagination when only one page', async () => {
      const recipes = [createRecipe()];
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(recipes, 1, 1, 12))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument();
      });

      expect(
        screen.queryByRole('button', { name: /previous/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /next/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('recipe detail dialog', () => {
    it('should open recipe detail dialog when recipe is clicked', async () => {
      const user = userEvent.setup();
      const recipe = createRecipe({ name: 'Test Recipe' });
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([recipe]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument();
      });

      await user.click(
        screen.getByRole('button', { name: /view test recipe details/i })
      );

      await waitFor(() => {
        // Dialog should open with recipe details
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA region label', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByRole('region', { name: /recipe browser/i })
        ).toBeInTheDocument();
      });
    });

    it('should have heading for the section', async () => {
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { name: /recipe browser/i })
        ).toBeInTheDocument();
      });
    });

    it('should have recipe list with proper role', async () => {
      const recipes = [createRecipe()];
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse(recipes))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(screen.getByRole('list', { name: /recipe list/i })).toBeInTheDocument();
      });
    });

    it('should have accessible button labels for recipe cards', async () => {
      const recipe = createRecipe({ name: 'Delicious Pasta' });
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([recipe]))
      );

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /view delicious pasta details/i })
        ).toBeInTheDocument();
      });
    });
  });

  describe('error state', () => {
    it('should show error message when API fails', async () => {
      mockRecipesApi.list.mockRejectedValue(new Error('API Error'));

      renderWithQuery(<RecipeBrowser />);

      await waitFor(() => {
        expect(
          screen.getByText(/failed to load recipes/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('initialIngredient prop', () => {
    it('should pre-populate search input with initialIngredient', async () => {
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', []))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="chicken" />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by ingredient/i)
        ).toHaveValue('chicken');
      });
    });

    it('should automatically search for initialIngredient on mount', async () => {
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', []))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="chicken" />);

      await waitFor(() => {
        expect(mockRecipesApi.searchByIngredient).toHaveBeenCalledWith(
          'chicken',
          1,
          12
        );
      });
    });

    it('should show search results from initialIngredient', async () => {
      const searchResults = [
        createRecipe({ name: 'Chicken Curry' }),
        createRecipe({ name: 'Grilled Chicken' }),
      ];
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', searchResults))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="chicken" />);

      await waitFor(() => {
        expect(screen.getByText('Chicken Curry')).toBeInTheDocument();
        expect(screen.getByText('Grilled Chicken')).toBeInTheDocument();
      });
    });

    it('should show active search indicator with initialIngredient', async () => {
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('milk', [], 0))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="milk" />);

      await waitFor(() => {
        expect(
          screen.getByText(/showing recipes containing:/i)
        ).toBeInTheDocument();
        expect(screen.getByText('milk')).toBeInTheDocument();
      });
    });

    it('should not call list API when initialIngredient is provided', async () => {
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('eggs', []))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="eggs" />);

      await waitFor(() => {
        expect(mockRecipesApi.searchByIngredient).toHaveBeenCalled();
      });

      // List API should not be called when searching
      expect(mockRecipesApi.list).not.toHaveBeenCalled();
    });

    it('should allow clearing initialIngredient search', async () => {
      const user = userEvent.setup();
      mockRecipesApi.searchByIngredient.mockResolvedValue(
        mockAxiosResponse(createRecipeSearchResponse('chicken', [createRecipe()]))
      );
      mockRecipesApi.list.mockResolvedValue(
        mockAxiosResponse(createRecipeListResponse([]))
      );

      renderWithQuery(<RecipeBrowser initialIngredient="chicken" />);

      await waitFor(() => {
        expect(screen.getByText('Clear')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Clear'));

      await waitFor(() => {
        // After clearing, the list API should be called
        expect(mockRecipesApi.list).toHaveBeenCalled();
      });
    });
  });
});
