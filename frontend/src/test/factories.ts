import type { User, Recipe, MealSlot, MealPlan, FridgeItem, AdaptiveOutput, AdaptationReason, CatchUpSuggestions, ExpiringItem, PendingMeal, PrepStep, OptimizedPrepTimeline } from '@/types';

// Counter for unique IDs
let idCounter = 0;
const genId = () => `test-${++idCounter}`;

/**
 * Factory functions for creating test data
 * Each factory returns valid default data that can be overridden
 */

export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: genId(),
    email: 'test@example.com',
    full_name: null,
    diet_type: 'low_histamine',
    dietary_exclusions: [],
    role: 'user',
    is_active: true,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

export function createRecipe(overrides: Partial<Recipe> = {}): Recipe {
  return {
    id: genId(),
    name: 'Test Recipe',
    meal_type: 'lunch',
    ingredients: [
      { name: 'Chicken', quantity: '200g', freshness_days: 5 },
      { name: 'Rice', quantity: '100g', freshness_days: 30 },
    ],
    prep_steps: ['Step 1', 'Step 2'],
    prep_time_minutes: 30,
    reusability_index: 0.5,
    diet_tags: ['high-protein'],
    servings: 2,
    ...overrides,
  };
}

export function createMealSlot(overrides: Partial<MealSlot> = {}): MealSlot {
  return {
    id: genId(),
    date: new Date().toISOString().split('T')[0],
    meal_type: 'lunch',
    prep_status: 'PENDING',
    prep_completed_at: null,
    recipe: createRecipe(),
    ...overrides,
  };
}

export function createMealPlan(overrides: Partial<MealPlan> = {}): MealPlan {
  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 2);

  return {
    id: genId(),
    diet_type: 'low_histamine',
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    meals: [
      createMealSlot({ meal_type: 'breakfast', date: startDate.toISOString().split('T')[0] }),
      createMealSlot({ meal_type: 'lunch', date: startDate.toISOString().split('T')[0] }),
      createMealSlot({ meal_type: 'dinner', date: startDate.toISOString().split('T')[0] }),
    ],
    ...overrides,
  };
}

export function createFridgeItem(overrides: Partial<FridgeItem> = {}): FridgeItem {
  return {
    id: genId(),
    ingredient_name: 'Chicken Breast',
    quantity: '500g',
    days_remaining: 5,
    original_freshness_days: 7,
    added_date: new Date().toISOString(),
    freshness_percentage: 71,
    ...overrides,
  };
}

export function createAdaptationReason(overrides: Partial<AdaptationReason> = {}): AdaptationReason {
  return {
    type: 'substitute',
    affected_date: new Date().toISOString().split('T')[0],
    original_meal: 'Original Recipe',
    new_meal: 'Quick Alternative',
    reason: 'Substituted to use expiring ingredients',
    ...overrides,
  };
}

export function createAdaptiveOutput(overrides: Partial<AdaptiveOutput> = {}): AdaptiveOutput {
  return {
    new_plan: createMealPlan(),
    adaptation_summary: [createAdaptationReason()],
    grocery_adjustments: [],
    priority_ingredients: ['Chicken', 'Spinach'],
    estimated_recovery_time_minutes: 15,
    ...overrides,
  };
}

export function createExpiringItem(overrides: Partial<ExpiringItem> = {}): ExpiringItem {
  return {
    name: 'Spinach',
    days_remaining: 2,
    quantity: '200g',
    ...overrides,
  };
}

export function createPendingMeal(overrides: Partial<PendingMeal> = {}): PendingMeal {
  return {
    date: new Date().toISOString().split('T')[0],
    meal_type: 'lunch',
    recipe: 'Test Recipe',
    ...overrides,
  };
}

export function createCatchUpSuggestions(overrides: Partial<CatchUpSuggestions> = {}): CatchUpSuggestions {
  return {
    missed_preps: [],
    expiring_items: [],
    pending_meals: [],
    needs_adaptation: false,
    ...overrides,
  };
}

export function createPrepStep(overrides: Partial<PrepStep> = {}): PrepStep {
  return {
    step_number: 1,
    action: 'Chop onions',
    ingredient: 'onion',
    duration_minutes: 5,
    can_batch: true,
    batch_key: 'chop_onion',
    source_recipes: [],
    equipment: null,
    is_passive: false,
    phase: null,
    ...overrides,
  };
}

export function createOptimizedPrepTimeline(overrides: Partial<OptimizedPrepTimeline> = {}): OptimizedPrepTimeline {
  return {
    total_time_minutes: 45,
    steps: [
      createPrepStep({ step_number: 1, action: 'Chop all onions at once (for 2 recipes)', duration_minutes: 5 }),
      createPrepStep({ step_number: 2, action: 'Wash vegetables', ingredient: 'vegetables', duration_minutes: 3, can_batch: true, batch_key: 'wash_vegetables' }),
      createPrepStep({ step_number: 3, action: 'Preheat oven to 400F', ingredient: null, duration_minutes: 5, can_batch: false, batch_key: null }),
      createPrepStep({ step_number: 4, action: 'Season chicken breast', ingredient: 'chicken', duration_minutes: 2, can_batch: false, batch_key: null }),
      createPrepStep({ step_number: 5, action: 'Bake for 25 minutes', ingredient: null, duration_minutes: 25, can_batch: false, batch_key: null }),
    ],
    batched_savings_minutes: 8,
    prep_date: new Date().toISOString().split('T')[0],
    ...overrides,
  };
}

// Helper to reset ID counter between tests
export function resetIdCounter() {
  idCounter = 0;
}
