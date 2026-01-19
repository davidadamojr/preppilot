'use client';

import { Recipe } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { formatDietTag } from '@/lib/utils';

interface RecipeDetailDialogProps {
  recipe: Recipe | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RecipeDetailDialog({
  recipe,
  open,
  onOpenChange,
}: RecipeDetailDialogProps) {
  if (!recipe) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="text-xl">{recipe.name}</DialogTitle>
          <DialogDescription className="flex items-center gap-2 pt-1 flex-wrap">
            <span>{recipe.prep_time_minutes} min prep</span>
            <span className="text-gray-400">|</span>
            <span className="capitalize">{recipe.meal_type}</span>
            {recipe.servings && (
              <>
                <span className="text-gray-400">|</span>
                <span>{recipe.servings} {recipe.servings === 1 ? 'serving' : 'servings'}</span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Diet Tags */}
          {recipe.diet_tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {recipe.diet_tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  {formatDietTag(tag)}
                </Badge>
              ))}
            </div>
          )}

          {/* Ingredients Section */}
          <div>
            <h3 className="font-semibold text-sm uppercase tracking-wide text-gray-600 mb-3">
              Ingredients
            </h3>
            <ul className="space-y-2" role="list" aria-label="Ingredients list">
              {recipe.ingredients.map((ingredient, index) => (
                <li
                  key={index}
                  className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0"
                >
                  <span className="capitalize">{ingredient.name}</span>
                  <span className="text-gray-500 text-sm">
                    {ingredient.quantity}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Prep Steps Section */}
          <div>
            <h3 className="font-semibold text-sm uppercase tracking-wide text-gray-600 mb-3">
              Prep Steps
            </h3>
            <ol
              className="space-y-3"
              role="list"
              aria-label="Preparation steps"
            >
              {recipe.prep_steps.map((step, index) => (
                <li key={index} className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-sm font-medium flex items-center justify-center">
                    {index + 1}
                  </span>
                  <span className="text-gray-700 pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Additional Info */}
          {recipe.reusability_index > 0 && (
            <div className="flex items-center gap-2 text-sm text-gray-600 border-t pt-4">
              <span className="font-medium">Ingredient Reusability:</span>
              <Badge variant="outline" className="font-normal">
                {recipe.reusability_index} shared ingredients
              </Badge>
              <span className="text-gray-400 text-xs">(ingredients used in other recipes this week)</span>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
