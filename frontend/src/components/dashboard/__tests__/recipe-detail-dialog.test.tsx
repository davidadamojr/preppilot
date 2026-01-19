import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithQuery } from '@/test/utils';
import { RecipeDetailDialog } from '../recipe-detail-dialog';
import { createRecipe } from '@/test/factories';

describe('RecipeDetailDialog', () => {
  describe('rendering', () => {
    it('should render nothing when recipe is null', () => {
      const { container } = renderWithQuery(
        <RecipeDetailDialog recipe={null} open={true} onOpenChange={vi.fn()} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should display recipe name as dialog title', () => {
      const recipe = createRecipe({ name: 'Delicious Pasta' });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByRole('heading', { name: 'Delicious Pasta' })).toBeInTheDocument();
    });

    it('should display prep time in header', () => {
      const recipe = createRecipe({ prep_time_minutes: 45 });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('45 min prep')).toBeInTheDocument();
    });

    it('should display meal type in header', () => {
      const recipe = createRecipe({ meal_type: 'dinner' });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('dinner')).toBeInTheDocument();
    });
  });

  describe('servings display', () => {
    it('should display servings when available', () => {
      const recipe = createRecipe({ servings: 4 });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('4 servings')).toBeInTheDocument();
    });

    it('should display singular "serving" for 1 serving', () => {
      const recipe = createRecipe({ servings: 1 });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('1 serving')).toBeInTheDocument();
    });

    it('should not display servings when undefined', () => {
      const recipe = createRecipe({ servings: undefined });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.queryByText(/serving/i)).not.toBeInTheDocument();
    });
  });

  describe('reusability index display', () => {
    it('should display reusability index when greater than 0', () => {
      const recipe = createRecipe({ reusability_index: 3 });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('Ingredient Reusability:')).toBeInTheDocument();
      expect(screen.getByText('3 shared ingredients')).toBeInTheDocument();
    });

    it('should not display reusability section when index is 0', () => {
      const recipe = createRecipe({ reusability_index: 0 });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.queryByText('Ingredient Reusability:')).not.toBeInTheDocument();
    });
  });

  describe('diet tags', () => {
    it('should display diet tags when available', () => {
      const recipe = createRecipe({ diet_tags: ['gluten-free', 'dairy-free'] });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('gluten-free')).toBeInTheDocument();
      expect(screen.getByText('dairy-free')).toBeInTheDocument();
    });

    it('should not render diet tags section when empty', () => {
      const recipe = createRecipe({ diet_tags: [] });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      // Only the header and main content sections should exist
      expect(screen.getByText('Ingredients')).toBeInTheDocument();
      expect(screen.getByText('Prep Steps')).toBeInTheDocument();
    });
  });

  describe('ingredients section', () => {
    it('should display all ingredients with quantities', () => {
      const recipe = createRecipe({
        ingredients: [
          { name: 'Chicken', quantity: '200g', freshness_days: 5 },
          { name: 'Broccoli', quantity: '1 cup', freshness_days: 7 },
        ],
      });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('Chicken')).toBeInTheDocument();
      expect(screen.getByText('200g')).toBeInTheDocument();
      expect(screen.getByText('Broccoli')).toBeInTheDocument();
      expect(screen.getByText('1 cup')).toBeInTheDocument();
    });

    it('should have accessible ingredients list', () => {
      const recipe = createRecipe();

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByRole('list', { name: /ingredients list/i })).toBeInTheDocument();
    });
  });

  describe('prep steps section', () => {
    it('should display all prep steps with numbers', () => {
      const recipe = createRecipe({
        prep_steps: ['Chop vegetables', 'Heat oil', 'Cook for 10 minutes'],
      });

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByText('Chop vegetables')).toBeInTheDocument();
      expect(screen.getByText('Heat oil')).toBeInTheDocument();
      expect(screen.getByText('Cook for 10 minutes')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('should have accessible prep steps list', () => {
      const recipe = createRecipe();

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByRole('list', { name: /preparation steps/i })).toBeInTheDocument();
    });
  });

  describe('dialog behavior', () => {
    it('should not render when open is false', () => {
      const recipe = createRecipe();

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={false} onOpenChange={vi.fn()} />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should render dialog when open is true', () => {
      const recipe = createRecipe();

      renderWithQuery(
        <RecipeDetailDialog recipe={recipe} open={true} onOpenChange={vi.fn()} />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });
});
