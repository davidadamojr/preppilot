// User role enum matching backend UserRole
export type UserRole = 'user' | 'admin';

// Diet type enum matching backend DietType (backend/models/schemas.py:45-51)
export type DietType = 'low_histamine' | 'low_histamine_low_oxalate' | 'fodmap' | 'fructose_free';

// Prep status enum matching backend PrepStatus (backend/models/schemas.py:52-56)
export type PrepStatus = 'PENDING' | 'DONE' | 'SKIPPED';

// Dietary exclusion enum matching backend DietaryExclusion (backend/models/schemas.py:59-88)
export type DietaryExclusion =
  | 'peanuts'
  | 'tree_nuts'
  | 'shellfish'
  | 'fish'
  | 'eggs'
  | 'milk'
  | 'soy'
  | 'wheat'
  | 'sesame'
  | 'gluten'
  | 'dairy'
  | 'nightshades'
  | 'seafood'
  | 'celery'
  | 'mustard'
  | 'sulfites'
  | 'corn'
  | 'all_nuts'
  | 'all_seafood'
  | 'red_meat'
  | 'poultry'
  | 'pork';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  diet_type: DietType;
  dietary_exclusions: DietaryExclusion[];
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface DietaryExclusionOption {
  name: string;
  value: string;
}

export interface Ingredient {
  name: string;
  quantity: string;
  freshness_days: number;
  category?: string; // Optional: protein, vegetable, herb, etc.
}

export interface Recipe {
  id: string;
  name: string;
  meal_type: string;
  ingredients: Ingredient[];
  prep_steps: string[];
  prep_time_minutes: number;
  reusability_index: number;
  diet_tags: string[];
  servings?: number;
}

export interface MealSlot {
  id: string;
  date: string;
  meal_type: string;
  prep_status: PrepStatus;
  prep_completed_at: string | null;
  recipe: Recipe;
}

export interface MealPlan {
  id: string;
  diet_type: DietType;
  start_date: string;
  end_date: string;
  created_at: string;
  updated_at: string;
  meals: MealSlot[];
}

export interface FridgeItem {
  id: string;
  ingredient_name: string;
  quantity: string;
  days_remaining: number;
  original_freshness_days: number;
  added_date: string;
  freshness_percentage: number;
}

// Matches backend AdaptationReason schema from backend/models/schemas.py
export interface AdaptationReason {
  type: 'reorder' | 'substitute' | 'simplify' | 'skip';
  affected_date: string;
  original_meal?: string;
  new_meal?: string;
  reason: string;
}

// Matches backend AdaptiveEngineOutput schema from backend/models/schemas.py
export interface AdaptiveOutput {
  new_plan: MealPlan;
  adaptation_summary: AdaptationReason[];
  grocery_adjustments: string[];
  priority_ingredients: string[];
  estimated_recovery_time_minutes: number;
}

export interface CatchUpSuggestion {
  original_meal: string;
  simplified_alternative: string;
  time_saved_minutes: number;
  reason: string;
}

// Response type for GET /api/plans/{id}/catch-up endpoint
export interface ExpiringItem {
  name: string;
  days_remaining: number;
  quantity: string;
}

export interface PendingMeal {
  date: string;
  meal_type: string;
  recipe: string;
}

export interface CatchUpSuggestions {
  missed_preps: string[];
  expiring_items: ExpiringItem[];
  pending_meals: PendingMeal[];
  needs_adaptation: boolean;
}

// Email API response types
export interface EmailResponse {
  success: boolean;
  message: string;
}

export interface EmailStatus {
  enabled: boolean;
  user_email: string;
  smtp_configured: boolean;
}

// Recipe list pagination response (matches backend RecipeListResponse)
export interface RecipeListResponse {
  recipes: Recipe[];
  total: number;
  page: number;
  page_size: number;
}

// Recipe search by ingredient response
export interface RecipeSearchResponse {
  ingredient: string;
  matching_recipes: Recipe[];
  count: number;
  total: number;
  page: number;
  page_size: number;
}

// Equipment types (matches backend EquipmentType enum)
export type EquipmentType = 'oven' | 'stovetop' | 'prep_area' | 'hands_free';

// Cooking phase types (matches backend CookingPhase enum)
export type CookingPhase = 'prep' | 'cooking' | 'finishing';

// Prep timeline types (matches backend PrepStep and OptimizedPrepTimeline)
export interface PrepStep {
  step_number: number;
  action: string;
  ingredient: string | null;
  duration_minutes: number;
  can_batch: boolean;
  batch_key: string | null;
  source_recipes: string[];
  equipment: EquipmentType | null;
  is_passive: boolean;
  phase: CookingPhase | null;
}

export interface OptimizedPrepTimeline {
  total_time_minutes: number;
  steps: PrepStep[];
  batched_savings_minutes: number;
  prep_date: string;
}

// Compatible recipe for swap (simplified version without full ingredients)
export interface CompatibleRecipe {
  id: string;
  name: string;
  meal_type: string;
  prep_time_minutes: number;
  diet_tags: string[];
  servings: number;
}

// Response from GET /api/plans/{plan_id}/compatible-recipes
export interface CompatibleRecipesResponse {
  recipes: CompatibleRecipe[];
  total: number;
}

// Feature flag names matching backend Feature enum (backend/features/flags.py)
export type FeatureName =
  | 'email_plan_notifications'
  | 'email_expiring_alerts'
  | 'email_adaptation_summaries'
  | 'export_pdf'
  | 'export_shopping_list'
  | 'plan_duplication'
  | 'plan_adaptation'
  | 'meal_swap'
  | 'fridge_bulk_import'
  | 'fridge_expiring_notifications'
  | 'recipe_search'
  | 'recipe_browser'
  | 'admin_user_management'
  | 'admin_audit_logs'
  | 'prep_timeline_optimization'
  | 'llm_step_parsing'
  | 'offline_mode';

// Response from GET /api/features
export interface FeatureFlagsResponse {
  flags: Record<FeatureName, boolean>;
}

// Error response structure for FEATURE_DISABLED errors
export interface FeatureDisabledError {
  error_code: 'FEATURE_DISABLED';
  message: string;
  feature: FeatureName;
}
