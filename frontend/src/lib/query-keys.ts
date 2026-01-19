/**
 * Centralized query key factory for React Query.
 *
 * All query keys that store user-specific data MUST include the user ID
 * to prevent cache collisions when users log in/out on the same browser.
 *
 * Pattern:
 * - User-scoped data: ['resource', userId, ...rest]
 * - Global data: ['resource', ...rest] (no user ID)
 *
 * Benefits:
 * - Cache isolation between users
 * - Consistent key structure across components
 * - Easy cache invalidation with partial key matching
 * - Type-safe key generation
 */

// Type for user ID (can be undefined if not logged in)
type UserId = string | undefined;

/**
 * Query keys for fridge-related data.
 * Fridge items are user-specific, so all keys include userId.
 */
export const fridgeKeys = {
  /** Base key for all fridge queries - use for broad invalidation */
  all: (userId: UserId) => ['fridge', userId] as const,

  /** Key for fetching all fridge items */
  list: (userId: UserId) => [...fridgeKeys.all(userId), 'list'] as const,

  /** Key for fetching expiring fridge items */
  expiring: (userId: UserId, threshold: number) =>
    [...fridgeKeys.all(userId), 'expiring', threshold] as const,
};

/**
 * Query keys for meal plan-related data.
 * Plans are user-specific, so all keys include userId.
 */
export const planKeys = {
  /** Base key for all plan queries - use for broad invalidation */
  all: (userId: UserId) => ['plans', userId] as const,

  /** Key for fetching paginated plan list */
  list: (userId: UserId, limit?: number) =>
    limit !== undefined
      ? ([...planKeys.all(userId), 'list', limit] as const)
      : ([...planKeys.all(userId), 'list'] as const),

  /** Key for fetching a single plan by ID */
  detail: (userId: UserId, planId: string) =>
    [...planKeys.all(userId), 'detail', planId] as const,

  /** Key for fetching catch-up suggestions for a plan */
  catchup: (userId: UserId, planId: string | undefined) =>
    [...planKeys.all(userId), 'catchup', planId] as const,

  /** Key for fetching prep timeline for a specific date */
  prepTimeline: (userId: UserId, planId: string, date: string) =>
    [...planKeys.all(userId), 'prep-timeline', planId, date] as const,

  /** Key for fetching compatible recipes for meal swap */
  compatibleRecipes: (userId: UserId, planId: string, mealType: string | undefined) =>
    [...planKeys.all(userId), 'compatible-recipes', planId, mealType] as const,
};

/**
 * Query keys for recipe-related data.
 * Recipes are global (not user-specific), so no userId is included.
 * However, recipe searches/filters are user-independent.
 */
export const recipeKeys = {
  /** Base key for all recipe queries */
  all: () => ['recipes'] as const,

  /** Key for fetching paginated recipe list with filters */
  list: (filters: { mealType?: string; dietTag?: string; page?: number }) =>
    [...recipeKeys.all(), 'list', filters.mealType, filters.dietTag, filters.page] as const,

  /** Key for searching recipes by ingredient */
  search: (ingredient: string, page?: number) =>
    [...recipeKeys.all(), 'search', ingredient, page] as const,
};

/**
 * Query keys for exclusions (global, static data).
 * Available exclusions are the same for all users, so no userId needed.
 */
export const exclusionKeys = {
  /** Key for fetching available dietary exclusions */
  available: () => ['availableExclusions'] as const,
};

/**
 * Legacy export for backward compatibility with existing useAvailableExclusions hook.
 * @deprecated Use exclusionKeys.available() instead
 */
export const EXCLUSIONS_QUERY_KEY = exclusionKeys.available();

/**
 * Query keys for feature flags.
 * Feature flags are global configuration, but we scope by userId to ensure
 * cache is cleared on logout and fresh flags are fetched on login.
 */
export const featureFlagKeys = {
  /** Base key for all feature flag queries */
  all: (userId: UserId) => ['featureFlags', userId] as const,

  /** Key for fetching all feature flags */
  flags: (userId: UserId) => [...featureFlagKeys.all(userId), 'flags'] as const,
};
