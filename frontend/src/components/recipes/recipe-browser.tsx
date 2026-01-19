'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { recipesApi } from '@/lib/api';
import { recipeKeys } from '@/lib/query-keys';
import { Recipe, RecipeListResponse, RecipeSearchResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { RecipeDetailDialog } from '@/components/dashboard/recipe-detail-dialog';
import { RecipeGridSkeleton } from '@/components/dashboard/skeletons';
import { Clock, ChefHat, Search, X } from 'lucide-react';
import { formatDietTag } from '@/lib/utils';

const MEAL_TYPES = [
  { value: '', label: 'All Meal Types' },
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
];

const DIET_TAGS = [
  { value: '', label: 'All Diet Tags' },
  { value: 'low-histamine', label: 'Low Histamine' },
  { value: 'gluten-free', label: 'Gluten Free' },
  { value: 'dairy-free', label: 'Dairy Free' },
  { value: 'high-protein', label: 'High Protein' },
  { value: 'vegetarian', label: 'Vegetarian' },
];

const PAGE_SIZE = 12;

interface RecipeBrowserProps {
  /** Initial ingredient to search for (e.g., from URL params or expiring items) */
  initialIngredient?: string;
}

export function RecipeBrowser({ initialIngredient }: RecipeBrowserProps) {
  const [mealType, setMealType] = useState('');
  const [dietTag, setDietTag] = useState('');
  const [searchIngredient, setSearchIngredient] = useState(initialIngredient || '');
  const [activeSearch, setActiveSearch] = useState(initialIngredient || '');
  const [page, setPage] = useState(1);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Update search when initialIngredient changes (e.g., navigation with different params)
  useEffect(() => {
    if (initialIngredient) {
      setSearchIngredient(initialIngredient);
      setActiveSearch(initialIngredient);
      setPage(1);
    }
  }, [initialIngredient]);

  // Main recipe list query (recipes are global, no user ID needed)
  const {
    data: recipeListData,
    isLoading: isListLoading,
    error: listError,
  } = useQuery({
    queryKey: recipeKeys.list({ mealType: mealType || undefined, dietTag: dietTag || undefined, page }),
    queryFn: async () => {
      const response = await recipesApi.list({
        mealType: mealType || undefined,
        dietTag: dietTag || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      return response.data as RecipeListResponse;
    },
    enabled: !activeSearch,
  });

  // Ingredient search query (recipes are global, no user ID needed)
  const {
    data: searchData,
    isLoading: isSearchLoading,
    error: searchError,
  } = useQuery({
    queryKey: recipeKeys.search(activeSearch, page),
    queryFn: async () => {
      const response = await recipesApi.searchByIngredient(activeSearch, page, PAGE_SIZE);
      return response.data as RecipeSearchResponse;
    },
    enabled: !!activeSearch,
  });

  const isLoading = activeSearch ? isSearchLoading : isListLoading;
  const error = activeSearch ? searchError : listError;
  const recipes = activeSearch
    ? searchData?.matching_recipes || []
    : recipeListData?.recipes || [];
  const totalRecipes = activeSearch ? searchData?.total || 0 : recipeListData?.total || 0;
  const totalPages = Math.ceil(totalRecipes / PAGE_SIZE);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchIngredient.trim()) {
      setActiveSearch(searchIngredient.trim());
      setPage(1);
    }
  };

  const clearSearch = () => {
    setSearchIngredient('');
    setActiveSearch('');
    setPage(1);
  };

  const handleFilterChange = (filterType: 'mealType' | 'dietTag', value: string) => {
    if (filterType === 'mealType') {
      setMealType(value);
    } else {
      setDietTag(value);
    }
    setPage(1);
    clearSearch();
  };

  const handleRecipeClick = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setIsDialogOpen(true);
  };

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-red-600">Failed to load recipes. Please try again.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6" role="region" aria-label="Recipe Browser">
      <div>
        <h2 className="text-xl font-semibold" id="recipes-heading">
          Recipe Browser
        </h2>
        <p className="text-sm text-gray-600">
          Browse and search recipes by meal type, diet tag, or ingredient
        </p>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="space-y-4">
            {/* Ingredient Search */}
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="flex-1">
                <Label htmlFor="ingredient-search" className="sr-only">
                  Search by ingredient
                </Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="ingredient-search"
                    type="text"
                    placeholder="Search by ingredient (e.g., chicken, rice)"
                    value={searchIngredient}
                    onChange={(e) => setSearchIngredient(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Button type="submit" disabled={!searchIngredient.trim()}>
                Search
              </Button>
              {activeSearch && (
                <Button type="button" variant="outline" onClick={clearSearch}>
                  <X className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              )}
            </form>

            {/* Filters */}
            {!activeSearch && (
              <div className="flex gap-4 flex-wrap">
                <div className="min-w-[160px]">
                  <Label htmlFor="meal-type-filter" className="text-xs text-gray-500 mb-1 block">
                    Meal Type
                  </Label>
                  <select
                    id="meal-type-filter"
                    value={mealType}
                    onChange={(e) => handleFilterChange('mealType', e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                  >
                    {MEAL_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="min-w-[160px]">
                  <Label htmlFor="diet-tag-filter" className="text-xs text-gray-500 mb-1 block">
                    Diet Tag
                  </Label>
                  <select
                    id="diet-tag-filter"
                    value={dietTag}
                    onChange={(e) => handleFilterChange('dietTag', e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                  >
                    {DIET_TAGS.map((tag) => (
                      <option key={tag.value} value={tag.value}>
                        {tag.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Active Search Indicator */}
            {activeSearch && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>
                  Showing recipes containing: <strong>{activeSearch}</strong>
                </span>
                <span>({totalRecipes} found)</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && <RecipeGridSkeleton />}

      {/* Results */}
      {!isLoading && recipes.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <ChefHat className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">
              {activeSearch
                ? `No recipes found containing "${activeSearch}"`
                : 'No recipes found with the selected filters.'}
            </p>
            {activeSearch && (
              <Button variant="link" onClick={clearSearch} className="mt-2">
                Clear search
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {!isLoading && recipes.length > 0 && (
        <>
          {/* Recipe Grid */}
          <div
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
            role="list"
            aria-label="Recipe list"
          >
            {recipes.map((recipe) => {
              const descriptionId = `recipe-desc-${recipe.id}`;
              const dietTagsText = recipe.diet_tags.length > 0
                ? `Diet tags: ${recipe.diet_tags.map(formatDietTag).join(', ')}.`
                : 'No diet tags.';
              return (
                <Card
                  key={recipe.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  role="listitem"
                  aria-describedby={descriptionId}
                >
                  <CardContent className="py-4">
                    {/* Visually hidden description for screen readers */}
                    <span id={descriptionId} className="sr-only">
                      {recipe.name}: {recipe.meal_type} recipe, {recipe.prep_time_minutes} minutes prep time,
                      {recipe.servings ? ` ${recipe.servings} servings,` : ''} {recipe.ingredients.length} ingredients,
                      {recipe.prep_steps.length} steps. {dietTagsText}
                    </span>
                    <button
                      className="w-full text-left"
                      onClick={() => handleRecipeClick(recipe)}
                      aria-label={`View ${recipe.name} details`}
                    >
                      <h3 className="font-semibold text-lg mb-2 line-clamp-1">{recipe.name}</h3>

                      <div className="flex items-center gap-3 text-sm text-gray-600 mb-3">
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" aria-hidden="true" />
                          {recipe.prep_time_minutes} min
                        </span>
                        <span className="capitalize">{recipe.meal_type}</span>
                        {recipe.servings && <span>{recipe.servings} servings</span>}
                      </div>

                      <div className="flex flex-wrap gap-1.5 mb-3" aria-hidden="true">
                        {recipe.diet_tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {formatDietTag(tag)}
                          </Badge>
                        ))}
                        {recipe.diet_tags.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{recipe.diet_tags.length - 3}
                          </Badge>
                        )}
                      </div>

                      <p className="text-sm text-gray-500">
                        {recipe.ingredients.length} ingredients • {recipe.prep_steps.length} steps
                      </p>
                    </button>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-gray-600 px-4">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}

          {/* Results Count */}
          <p className="text-sm text-gray-500 text-center">
            Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, totalRecipes)} of{' '}
            {totalRecipes} recipes
          </p>
        </>
      )}

      {/* Recipe Detail Dialog */}
      <RecipeDetailDialog
        recipe={selectedRecipe}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
}
