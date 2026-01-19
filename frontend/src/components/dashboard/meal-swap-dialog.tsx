'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { plansApi } from '@/lib/api';
import { planKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import { MealSlot, CompatibleRecipe, CompatibleRecipesResponse } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LoadingState } from '@/components/ui/spinner';
import { Clock, Check, ChefHat } from 'lucide-react';
import { formatDietTag } from '@/lib/utils';

interface MealSwapDialogProps {
  planId: string;
  meal: MealSlot | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSwap: (recipeId: string, recipe?: CompatibleRecipe) => Promise<void>;
}

export function MealSwapDialog({
  planId,
  meal,
  open,
  onOpenChange,
  onSwap,
}: MealSwapDialogProps) {
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);
  const [isSwapping, setIsSwapping] = useState(false);
  const { user } = useAuth();
  const userId = user?.id;

  const {
    data: recipesData,
    isLoading,
    error,
  } = useQuery({
    queryKey: planKeys.compatibleRecipes(userId, planId, meal?.meal_type),
    queryFn: async () => {
      if (!meal) return null;
      const response = await plansApi.getCompatibleRecipes(planId, meal.meal_type);
      return response.data as CompatibleRecipesResponse;
    },
    enabled: open && !!meal && !!userId,
  });

  const handleSwap = async () => {
    if (!selectedRecipeId) return;

    // Find the selected recipe to pass for optimistic update
    const selectedRecipe = availableRecipes.find((r) => r.id === selectedRecipeId);

    setIsSwapping(true);
    try {
      await onSwap(selectedRecipeId, selectedRecipe);
      onOpenChange(false);
      setSelectedRecipeId(null);
    } finally {
      setIsSwapping(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedRecipeId(null);
    }
    onOpenChange(newOpen);
  };

  if (!meal) return null;

  // Filter out the current recipe from the list
  const availableRecipes = recipesData?.recipes.filter(
    (recipe) => recipe.id !== meal.recipe.id
  ) || [];

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Swap Meal</DialogTitle>
          <DialogDescription>
            Choose a different recipe for{' '}
            <span className="font-medium capitalize">{meal.meal_type}</span> on{' '}
            <span className="font-medium">
              {(() => {
                // Parse as local time to avoid timezone shift
                const [year, month, day] = meal.date.split('-').map(Number);
                const date = new Date(year, month - 1, day);
                return date.toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                });
              })()}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {/* Current Recipe */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              Current Recipe
            </p>
            <p className="font-medium">{meal.recipe.name}</p>
            <p className="text-sm text-gray-600">
              {meal.recipe.prep_time_minutes} min prep
            </p>
          </div>

          {/* Loading State */}
          {isLoading && <LoadingState message="Loading compatible recipes..." />}

          {/* Error State */}
          {error && (
            <div className="text-center py-8">
              <p className="text-red-600">Failed to load recipes. Please try again.</p>
            </div>
          )}

          {/* No Recipes State */}
          {!isLoading && !error && availableRecipes.length === 0 && (
            <div className="text-center py-8">
              <ChefHat className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">
                No alternative recipes available for this meal type.
              </p>
            </div>
          )}

          {/* Recipe List */}
          {!isLoading && !error && availableRecipes.length > 0 && (
            <div className="space-y-2" role="listbox" aria-label="Available recipes">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                Available Recipes ({availableRecipes.length})
              </p>
              {availableRecipes.map((recipe) => (
                <button
                  key={recipe.id}
                  type="button"
                  role="option"
                  aria-selected={selectedRecipeId === recipe.id}
                  onClick={() => setSelectedRecipeId(recipe.id)}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                    selectedRecipeId === recipe.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{recipe.name}</span>
                        {selectedRecipeId === recipe.id && (
                          <Check className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
                        <Clock className="h-3.5 w-3.5" />
                        <span>{recipe.prep_time_minutes} min</span>
                        {recipe.servings && (
                          <>
                            <span className="text-gray-400">•</span>
                            <span>{recipe.servings} servings</span>
                          </>
                        )}
                      </div>
                      {recipe.diet_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {recipe.diet_tags.slice(0, 3).map((tag) => (
                            <Badge
                              key={tag}
                              variant="secondary"
                              className="text-xs"
                            >
                              {formatDietTag(tag)}
                            </Badge>
                          ))}
                          {recipe.diet_tags.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{recipe.diet_tags.length - 3}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isSwapping}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSwap}
            disabled={!selectedRecipeId || isSwapping}
          >
            {isSwapping ? 'Swapping...' : 'Swap Recipe'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
