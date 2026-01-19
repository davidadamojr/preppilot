import axios from 'axios';

function getApiBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;

  if (url) {
    return url;
  }

  // Allow localhost fallback only in development
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';
  }

  throw new Error(
    'NEXT_PUBLIC_API_URL environment variable is required in production. ' +
    'Please set it to your API server URL.'
  );
}

const API_BASE_URL = getApiBaseUrl();

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (email: string, password: string, dietType: string, dietaryExclusions: string[] = []) =>
    api.post('/auth/register', {
      email,
      password,
      diet_type: dietType,
      dietary_exclusions: dietaryExclusions
    }),

  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  getProfile: () => api.get('/auth/me'),

  updateExclusions: (exclusions: string[]) =>
    api.patch('/auth/me/exclusions', { dietary_exclusions: exclusions }),

  getAvailableExclusions: () => api.get('/auth/exclusions/available'),

  // Account management
  updateProfile: (data: { full_name?: string; diet_type?: string }) =>
    api.patch('/auth/me', {
      full_name: data.full_name,
      diet_type: data.diet_type,
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  deleteAccount: () => api.delete('/auth/me'),

  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),
};

// Plans API
export const plansApi = {
  generate: (days: number = 3, simplified: boolean = false, startDate?: string) => {
    const start_date = startDate || new Date().toISOString().split('T')[0];
    return api.post('/api/plans', { start_date, days, simplified });
  },

  list: (skip: number = 0, limit: number = 10) =>
    api.get('/api/plans', { params: { skip, limit } }),

  get: (id: string) => api.get(`/api/plans/${id}`),

  markPrep: (id: string, date: string, mealType: string, status: string) =>
    api.patch(`/api/plans/${id}/mark-prep`, {
      date,
      meal_type: mealType,
      status,
    }),

  adapt: (id: string) => api.post(`/api/plans/${id}/adapt`),

  getCatchUp: (id: string) => api.get(`/api/plans/${id}/catch-up`),

  delete: (id: string) => api.delete(`/api/plans/${id}`),

  getPrepTimeline: (id: string, prepDate: string) =>
    api.get(`/api/plans/${id}/prep-timeline`, {
      params: { prep_date: prepDate },
    }),

  swapMeal: (id: string, date: string, mealType: string, newRecipeId: string) =>
    api.patch(`/api/plans/${id}/swap-meal`, {
      date,
      meal_type: mealType,
      new_recipe_id: newRecipeId,
    }),

  getCompatibleRecipes: (id: string, mealType: string) =>
    api.get(`/api/plans/${id}/compatible-recipes`, {
      params: { meal_type: mealType },
    }),

  duplicate: (id: string, startDate: string) =>
    api.post(`/api/plans/${id}/duplicate`, { start_date: startDate }),
};

// Fridge API
export const fridgeApi = {
  get: () => api.get('/api/fridge'),

  addItem: (name: string, quantity: string, freshnessDays: number) =>
    api.post('/api/fridge/items', {
      ingredient_name: name,
      quantity,
      freshness_days: freshnessDays,
    }),

  addBulk: (items: Array<{ ingredient_name: string; quantity: string; freshness_days: number }>) =>
    api.post('/api/fridge/items/bulk', { items }),

  updateItem: (id: string, updates: { quantity?: string; days_remaining?: number }) =>
    api.patch(`/api/fridge/items/${id}`, updates),

  removeItem: (id: string) => api.delete(`/api/fridge/items/${id}`),

  removeByName: (name: string) => api.delete(`/api/fridge/items/by-name/${name}`),

  getExpiring: (threshold: number = 2) =>
    api.get('/api/fridge/expiring', { params: { threshold } }),

  clear: () => api.delete('/api/fridge'),
};

// Recipes API
export const recipesApi = {
  list: (params?: { mealType?: string; dietTag?: string; page?: number; pageSize?: number }) =>
    api.get('/api/recipes', {
      params: {
        meal_type: params?.mealType,
        diet_tag: params?.dietTag,
        page: params?.page ?? 1,
        page_size: params?.pageSize ?? 20,
      },
    }),

  get: (id: string) => api.get(`/api/recipes/${id}`),

  searchByIngredient: (ingredient: string, page: number = 1, pageSize: number = 20) =>
    api.get('/api/recipes/search/by-ingredient', {
      params: { ingredient, page, page_size: pageSize },
    }),
};

// Export API (PDF downloads)
export const exportApi = {
  downloadMealPlanPdf: (planId: string, includeShoppingList: boolean = true) =>
    api.get(`/api/export/${planId}/pdf`, {
      params: { include_shopping_list: includeShoppingList },
      responseType: 'blob',
    }),

  downloadCatchUpPdf: (planId: string, currentDate?: string) =>
    api.get(`/api/export/${planId}/catch-up-pdf`, {
      params: currentDate ? { current_date: currentDate } : {},
      responseType: 'blob',
    }),

  downloadShoppingListPdf: (planId: string) =>
    api.get(`/api/export/${planId}/shopping-list-pdf`, {
      responseType: 'blob',
    }),
};

// Email API
export const emailApi = {
  sendPlanEmail: (planId: string, includePdf: boolean = true) =>
    api.post(`/api/email/${planId}/send-plan`, { include_pdf: includePdf }),

  sendAdaptationEmail: (planId: string, currentDate?: string) =>
    api.post(`/api/email/${planId}/send-adaptation`, null, {
      params: currentDate ? { current_date: currentDate } : {},
    }),

  sendExpiringAlert: (daysThreshold: number = 2) =>
    api.post('/api/email/send-expiring-alert', null, {
      params: { days_threshold: daysThreshold },
    }),

  getStatus: () => api.get('/api/email/status'),
};

// Admin API (requires admin role)
export const adminApi = {
  // User management
  listUsers: (params?: {
    page?: number;
    pageSize?: number;
    role?: 'user' | 'admin';
    isActive?: boolean;
  }) =>
    api.get('/api/admin/users', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.pageSize ?? 20,
        role: params?.role,
        is_active: params?.isActive,
      },
    }),

  getUser: (userId: string) => api.get(`/api/admin/users/${userId}`),

  updateUserRole: (userId: string, role: 'user' | 'admin') =>
    api.patch(`/api/admin/users/${userId}/role`, { role }),

  updateUserStatus: (userId: string, isActive: boolean) =>
    api.patch(`/api/admin/users/${userId}/status`, { is_active: isActive }),

  deleteUser: (userId: string) => api.delete(`/api/admin/users/${userId}`),

  getStats: () => api.get('/api/admin/stats'),

  // Recipe management (admin CRUD)
  createRecipe: (recipe: {
    name: string;
    diet_tags: string[];
    meal_type: string;
    ingredients: Array<{
      name: string;
      quantity: string;
      freshness_days: number;
      category?: string;
    }>;
    prep_steps: string[];
    prep_time_minutes: number;
    reusability_index: number;
    servings?: number;
  }) => api.post('/api/recipes', recipe),

  updateRecipe: (
    recipeId: string,
    recipe: {
      name?: string;
      diet_tags?: string[];
      meal_type?: string;
      ingredients?: Array<{
        name: string;
        quantity: string;
        freshness_days: number;
        category?: string;
      }>;
      prep_steps?: string[];
      prep_time_minutes?: number;
      reusability_index?: number;
      servings?: number;
    }
  ) => api.put(`/api/recipes/${recipeId}`, recipe),

  deleteRecipe: (recipeId: string) => api.delete(`/api/recipes/${recipeId}`),
};

// Feature Flags API
export const featureFlagsApi = {
  /**
   * Get all feature flags for the current authenticated user.
   * Returns a map of feature names to their enabled state.
   */
  getAll: () => api.get('/api/features'),
};

/**
 * Helper to trigger a file download from a blob response.
 * Extracts filename from Content-Disposition header or uses fallback.
 */
export function downloadBlobAsFile(blob: Blob, fallbackFilename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fallbackFilename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
