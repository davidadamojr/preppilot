'use client';

import { useMemo, useCallback, useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ShoppingCart, Check } from 'lucide-react';
import type { MealPlan } from '@/types';

interface IngredientItem {
  ingredient_name: string;
  quantity: string;
  freshness_days: number;
  category?: string;
}

interface StockFridgeDialogProps {
  plan: MealPlan | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStock: (items: Array<{ ingredient_name: string; quantity: string; freshness_days: number }>) => Promise<void>;
  isLoading?: boolean;
}

/**
 * Formats a category name for display (e.g., "protein" -> "Protein")
 */
function formatCategory(category: string): string {
  return category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, ' ');
}

export function StockFridgeDialog({
  plan,
  open,
  onOpenChange,
  onStock,
  isLoading = false,
}: StockFridgeDialogProps) {
  // Track selected ingredients by name
  const [selectedIngredients, setSelectedIngredients] = useState<Set<string>>(new Set());

  // Extract and deduplicate ingredients from all meals in the plan
  const ingredients = useMemo(() => {
    if (!plan) return [];

    const ingredientMap = new Map<
      string,
      { quantity: string; freshness_days: number; category?: string }
    >();

    for (const meal of plan.meals) {
      for (const ing of meal.recipe.ingredients) {
        const key = ing.name.toLowerCase();
        const existing = ingredientMap.get(key);
        if (existing) {
          // Use minimum freshness (most conservative) for duplicates
          existing.freshness_days = Math.min(existing.freshness_days, ing.freshness_days);
        } else {
          ingredientMap.set(key, {
            quantity: ing.quantity,
            freshness_days: ing.freshness_days,
            category: ing.category,
          });
        }
      }
    }

    return Array.from(ingredientMap.entries()).map(([name, data]) => ({
      ingredient_name: name,
      ...data,
    }));
  }, [plan]);

  // Select all ingredients by default when dialog opens or ingredients change
  useEffect(() => {
    if (open && ingredients.length > 0) {
      setSelectedIngredients(new Set(ingredients.map((i) => i.ingredient_name)));
    }
  }, [open, ingredients]);

  // Reset selection when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedIngredients(new Set());
    }
  }, [open]);

  // Group ingredients by category for organized display
  const groupedIngredients = useMemo(() => {
    const groups: Record<string, IngredientItem[]> = {};
    for (const ing of ingredients) {
      const cat = ing.category || 'other';
      (groups[cat] ??= []).push(ing);
    }
    // Sort categories alphabetically, but put 'other' last
    const sortedEntries = Object.entries(groups).sort(([a], [b]) => {
      if (a === 'other') return 1;
      if (b === 'other') return -1;
      return a.localeCompare(b);
    });
    return sortedEntries;
  }, [ingredients]);

  const toggleIngredient = useCallback((ingredientName: string) => {
    setSelectedIngredients((prev) => {
      const next = new Set(prev);
      if (next.has(ingredientName)) {
        next.delete(ingredientName);
      } else {
        next.add(ingredientName);
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    if (selectedIngredients.size === ingredients.length) {
      // All selected, deselect all
      setSelectedIngredients(new Set());
    } else {
      // Select all
      setSelectedIngredients(new Set(ingredients.map((i) => i.ingredient_name)));
    }
  }, [selectedIngredients.size, ingredients]);

  const handleStock = useCallback(async () => {
    if (selectedIngredients.size === 0) return;

    const itemsToStock = ingredients
      .filter((i) => selectedIngredients.has(i.ingredient_name))
      .map(({ ingredient_name, quantity, freshness_days }) => ({
        ingredient_name,
        quantity,
        freshness_days,
      }));

    await onStock(itemsToStock);
  }, [ingredients, selectedIngredients, onStock]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      onOpenChange(false);
    }
  }, [isLoading, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Stock Fridge from Plan
          </DialogTitle>
          <DialogDescription>
            {plan ? (
              <>
                Add all ingredients from your meal plan ({plan.start_date} to {plan.end_date}) to
                your fridge.
              </>
            ) : (
              'No meal plan selected.'
            )}
          </DialogDescription>
        </DialogHeader>

        {plan && ingredients.length > 0 ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="secondary">
                  {selectedIngredients.size} of {ingredients.length} selected
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleAll}
                disabled={isLoading}
                className="text-xs"
              >
                {selectedIngredients.size === ingredients.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>

            <div className="border rounded-md p-3 bg-muted/30 max-h-64 overflow-y-auto space-y-4">
              {groupedIngredients.map(([category, items]) => (
                <div key={category}>
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    {formatCategory(category)}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {items.map((item) => {
                      const isSelected = selectedIngredients.has(item.ingredient_name);
                      return (
                        <button
                          key={item.ingredient_name}
                          type="button"
                          onClick={() => toggleIngredient(item.ingredient_name)}
                          disabled={isLoading}
                          className={`
                            inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                            border-2 transition-all cursor-pointer select-none
                            min-h-[44px] touch-manipulation
                            ${
                              isSelected
                                ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                                : 'bg-background text-foreground border-input hover:border-primary/50 hover:bg-muted'
                            }
                            active:scale-95
                            disabled:opacity-50 disabled:cursor-not-allowed
                          `}
                          aria-pressed={isSelected}
                          aria-label={`${isSelected ? 'Deselect' : 'Select'} ${item.ingredient_name}`}
                        >
                          <span
                            className={`
                              flex items-center justify-center w-5 h-5 rounded-md border-2 transition-colors
                              ${
                                isSelected
                                  ? 'bg-primary-foreground/20 border-primary-foreground/40'
                                  : 'border-muted-foreground/30'
                              }
                            `}
                          >
                            {isSelected && <Check className="h-3.5 w-3.5" />}
                          </span>
                          <span className="flex flex-col items-start leading-tight">
                            <span>{item.ingredient_name}</span>
                            <span className={`text-xs ${isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                              {item.quantity} · {item.freshness_days}d fresh
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs text-muted-foreground">
              Click ingredients to select/deselect. Duplicates are combined with conservative freshness.
            </p>
          </div>
        ) : plan ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No ingredients found in this meal plan.
          </p>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleStock}
            disabled={selectedIngredients.size === 0 || isLoading}
            aria-label={
              isLoading ? 'Adding ingredients to fridge' : `Add ${selectedIngredients.size} ingredients to fridge`
            }
          >
            {isLoading
              ? 'Adding...'
              : `Add ${selectedIngredients.size} Item${selectedIngredients.size !== 1 ? 's' : ''} to Fridge`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
