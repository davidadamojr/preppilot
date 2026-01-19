'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { plansApi, exportApi, emailApi, fridgeApi, downloadBlobAsFile } from '@/lib/api';
import { planKeys, fridgeKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import { MealPlan, MealSlot, Recipe, CompatibleRecipe } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { RecipeDetailDialog } from './recipe-detail-dialog';
import { PlanViewSkeleton } from './skeletons';
import { PrepTimelineDialog } from './prep-timeline-dialog';
import { PlanHistorySelector } from './plan-history-selector';
import { MealSwapDialog } from './meal-swap-dialog';
import { DuplicatePlanDialog } from './duplicate-plan-dialog';
import { GeneratePlanDialog } from './generate-plan-dialog';
import { StockFridgeDialog } from './stock-fridge-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, Mail, Clock, Trash2, RefreshCw, Copy, ShoppingCart } from 'lucide-react';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { FeatureGate, DisabledFeatureButton, FEATURE_LABELS } from '@/components/ui/feature-gate';
import { useFeatureFlags, isFeatureDisabledError } from '@/hooks/use-feature-flags';

const PLANS_PAGE_SIZE = 5;

export function PlanView() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [isRecipeDialogOpen, setIsRecipeDialogOpen] = useState(false);
  const [selectedTimelineDate, setSelectedTimelineDate] = useState<string | null>(null);
  const [isTimelineDialogOpen, setIsTimelineDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [plansLimit, setPlansLimit] = useState(PLANS_PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [swapMeal, setSwapMeal] = useState<MealSlot | null>(null);
  const [isSwapDialogOpen, setIsSwapDialogOpen] = useState(false);
  const [isDuplicateDialogOpen, setIsDuplicateDialogOpen] = useState(false);
  const [isDuplicating, setIsDuplicating] = useState(false);
  const [isStockDialogOpen, setIsStockDialogOpen] = useState(false);
  const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();
  const userId = user?.id;
  const { isEnabled } = useFeatureFlags();

  const handleTimelineClick = (date: string) => {
    setSelectedTimelineDate(date);
    setIsTimelineDialogOpen(true);
  };

  const handleRecipeClick = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setIsRecipeDialogOpen(true);
  };

  const handleSwapClick = (meal: MealSlot) => {
    setSwapMeal(meal);
    setIsSwapDialogOpen(true);
  };

  const handleSwapMeal = async (newRecipeId: string, newRecipe?: CompatibleRecipe) => {
    if (!currentPlan || !swapMeal) return;

    // Cancel any outgoing refetches
    await queryClient.cancelQueries({ queryKey: planKeys.all(userId) });

    // Snapshot the previous value
    const previousPlans = queryClient.getQueryData<MealPlan[]>(planKeys.list(userId, plansLimit));

    // Optimistically update the meal with new recipe (if recipe details provided)
    if (newRecipe) {
      // Convert CompatibleRecipe to full Recipe for optimistic update
      const optimisticRecipe: Recipe = {
        id: newRecipe.id,
        name: newRecipe.name,
        meal_type: newRecipe.meal_type,
        prep_time_minutes: newRecipe.prep_time_minutes,
        diet_tags: newRecipe.diet_tags,
        servings: newRecipe.servings,
        // These fields will be populated when we invalidate and refetch
        ingredients: [],
        prep_steps: [],
        reusability_index: 0,
      };

      queryClient.setQueryData<MealPlan[]>(planKeys.list(userId, plansLimit), (old) => {
        if (!old) return old;
        return old.map((plan) => {
          if (plan.id !== currentPlan.id) return plan;
          return {
            ...plan,
            meals: plan.meals.map((meal) => {
              if (meal.date !== swapMeal.date || meal.meal_type !== swapMeal.meal_type) return meal;
              return {
                ...meal,
                recipe: optimisticRecipe,
              };
            }),
          };
        });
      });
    }

    // Close dialog immediately
    setIsSwapDialogOpen(false);
    setSwapMeal(null);

    try {
      await plansApi.swapMeal(
        currentPlan.id,
        swapMeal.date,
        swapMeal.meal_type,
        newRecipeId
      );
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });
      toast({
        title: 'Meal swapped',
        description: 'Your meal has been updated with the new recipe.',
      });
    } catch (error) {
      // Rollback to previous state
      if (previousPlans) {
        queryClient.setQueryData(planKeys.list(userId, plansLimit), previousPlans);
      }
      // Handle feature disabled error gracefully
      if (isFeatureDisabledError(error)) {
        toast({
          title: 'Feature unavailable',
          description: FEATURE_LABELS.meal_swap + ' is currently unavailable.',
        });
      } else {
        toast({
          title: 'Swap failed',
          description: 'Could not swap the meal. Please try again.',
          variant: 'destructive',
        });
      }
      throw new Error('Swap failed');
    }
  };

  const handleExportPdf = async (planId: string, type: 'full' | 'shopping' | 'catchup') => {
    setIsExporting(true);
    try {
      let response;
      let filename: string;

      switch (type) {
        case 'full':
          response = await exportApi.downloadMealPlanPdf(planId);
          filename = `meal-plan.pdf`;
          break;
        case 'shopping':
          response = await exportApi.downloadShoppingListPdf(planId);
          filename = `shopping-list.pdf`;
          break;
        case 'catchup':
          response = await exportApi.downloadCatchUpPdf(planId);
          filename = `catch-up-summary.pdf`;
          break;
      }

      downloadBlobAsFile(response.data, filename);
      toast({
        title: 'PDF downloaded',
        description: `Your ${type === 'full' ? 'meal plan' : type === 'shopping' ? 'shopping list' : 'catch-up summary'} has been downloaded.`,
      });
    } catch (error) {
      // Handle feature disabled error gracefully
      if (isFeatureDisabledError(error)) {
        toast({
          title: 'Feature unavailable',
          description: FEATURE_LABELS.export_pdf + ' is currently unavailable.',
        });
      } else {
        toast({
          title: 'Export failed',
          description: 'Could not generate PDF. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setIsExporting(false);
    }
  };

  const handleSendEmail = async (planId: string, type: 'plan' | 'adaptation') => {
    setIsSendingEmail(true);
    try {
      if (type === 'plan') {
        await emailApi.sendPlanEmail(planId);
      } else {
        await emailApi.sendAdaptationEmail(planId);
      }
      toast({
        title: 'Email sent',
        description: `Your ${type === 'plan' ? 'meal plan' : 'adaptation summary'} has been sent to your email.`,
      });
    } catch {
      toast({
        title: 'Email failed',
        description: 'Could not send email. Please check your email settings and try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSendingEmail(false);
    }
  };

  const { data: plans, isLoading } = useQuery({
    queryKey: planKeys.list(userId, plansLimit),
    queryFn: async () => {
      const response = await plansApi.list(0, plansLimit);
      return response.data as MealPlan[];
    },
    enabled: !!userId,
  });

  // Auto-select the first plan when plans load or when the selected plan is deleted
  const currentPlan = selectedPlanId
    ? plans?.find((p) => p.id === selectedPlanId) || plans?.[0]
    : plans?.[0];

  // Update selectedPlanId when plans change and current selection is invalid
  const handleSelectPlan = useCallback((planId: string) => {
    setSelectedPlanId(planId);
  }, []);

  const handleLoadMorePlans = useCallback(async () => {
    setIsLoadingMore(true);
    setPlansLimit((prev) => prev + PLANS_PAGE_SIZE);
    // Query will automatically refetch due to plansLimit change
    setIsLoadingMore(false);
  }, []);

  // Determine if there might be more plans to load
  const hasMorePlans = plans?.length === plansLimit;

  const generateMutation = useMutation({
    mutationFn: async ({ startDate, days }: { startDate: string; days: number }) => {
      setIsGenerating(true);
      const response = await plansApi.generate(days, false, startDate);
      return { plan: response.data as MealPlan, days };
    },
    onSuccess: ({ plan, days }) => {
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });
      // Select the newly generated plan
      setSelectedPlanId(plan.id);
      setIsGenerateDialogOpen(false);
      toast({
        title: 'Meal plan generated!',
        description: `Your ${days}-day meal prep schedule is ready.`,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to generate plan',
        description: 'Please try again or check your connection.',
        variant: 'destructive',
      });
    },
    onSettled: () => {
      setIsGenerating(false);
    },
  });

  const markPrepMutation = useMutation({
    mutationFn: async ({ planId, date, mealType, status }: { planId: string; date: string; mealType: string; status: string }) => {
      return plansApi.markPrep(planId, date, mealType, status);
    },
    onMutate: async ({ planId, date, mealType, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: planKeys.all(userId) });

      // Snapshot the previous value
      const previousPlans = queryClient.getQueryData<MealPlan[]>(planKeys.list(userId, plansLimit));

      // Optimistically update the meal status
      queryClient.setQueryData<MealPlan[]>(planKeys.list(userId, plansLimit), (old) => {
        if (!old) return old;
        return old.map((plan) => {
          if (plan.id !== planId) return plan;
          return {
            ...plan,
            meals: plan.meals.map((meal) => {
              if (meal.date !== date || meal.meal_type !== mealType) return meal;
              return {
                ...meal,
                prep_status: status as 'PENDING' | 'DONE' | 'SKIPPED',
                prep_completed_at: status !== 'PENDING' ? new Date().toISOString() : null,
              };
            }),
          };
        });
      });

      return { previousPlans };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });
    },
    onError: (_error, _variables, context) => {
      // Rollback to previous state
      if (context?.previousPlans) {
        queryClient.setQueryData(planKeys.list(userId, plansLimit), context.previousPlans);
      }
      toast({
        title: 'Failed to update prep status',
        description: 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const stockFridgeMutation = useMutation({
    mutationFn: (items: Array<{ ingredient_name: string; quantity: string; freshness_days: number }>) =>
      fridgeApi.addBulk(items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
      toast({
        title: 'Fridge stocked',
        description: 'Ingredients from your meal plan have been added to your fridge.',
      });
      setIsStockDialogOpen(false);
    },
    onError: () => {
      toast({
        title: 'Failed to stock fridge',
        description: 'Could not add ingredients to fridge. Please try again.',
        variant: 'destructive',
      });
    },
  });

  const handleDeletePlan = async (planId: string) => {
    // Cancel any outgoing refetches
    await queryClient.cancelQueries({ queryKey: planKeys.all(userId) });

    // Snapshot the previous value
    const previousPlans = queryClient.getQueryData<MealPlan[]>(planKeys.list(userId, plansLimit));

    // Optimistically remove the plan
    queryClient.setQueryData<MealPlan[]>(planKeys.list(userId, plansLimit), (old) => {
      if (!old) return old;
      return old.filter((plan) => plan.id !== planId);
    });

    // Close dialog immediately
    setIsDeleteDialogOpen(false);

    // Reset selected plan if we deleted it
    if (selectedPlanId === planId) {
      setSelectedPlanId(null);
    }

    setIsDeleting(true);
    try {
      await plansApi.delete(planId);
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });
      toast({
        title: 'Plan deleted',
        description: 'Your meal plan has been deleted.',
      });
    } catch {
      // Rollback to previous state
      queryClient.setQueryData(planKeys.list(userId, plansLimit), previousPlans);
      setIsDeleteDialogOpen(true);
      if (selectedPlanId === null && previousPlans?.some((p) => p.id === planId)) {
        setSelectedPlanId(planId);
      }
      toast({
        title: 'Failed to delete plan',
        description: 'Could not delete the meal plan. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDuplicatePlan = async (startDate: string) => {
    if (!currentPlan) return;

    setIsDuplicating(true);
    try {
      const response = await plansApi.duplicate(currentPlan.id, startDate);
      const newPlan = response.data as MealPlan;

      // Close dialog and select the new plan
      setIsDuplicateDialogOpen(false);
      setSelectedPlanId(newPlan.id);

      // Invalidate queries to refresh the list
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });

      toast({
        title: 'Plan duplicated',
        description: 'Your meal plan has been duplicated with the new dates.',
      });
    } catch (error) {
      // Handle feature disabled error gracefully
      if (isFeatureDisabledError(error)) {
        toast({
          title: 'Feature unavailable',
          description: FEATURE_LABELS.plan_duplication + ' is currently unavailable.',
        });
      } else {
        toast({
          title: 'Failed to duplicate plan',
          description: 'Could not duplicate the meal plan. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setIsDuplicating(false);
    }
  };

  const groupMealsByDate = (meals: MealSlot[]) => {
    const grouped: Record<string, MealSlot[]> = {};
    meals.forEach((meal) => {
      if (!grouped[meal.date]) {
        grouped[meal.date] = [];
      }
      grouped[meal.date].push(meal);
    });
    return grouped;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DONE':
        return 'bg-green-100 text-green-800';
      case 'SKIPPED':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateStr: string) => {
    // Parse as local time to avoid timezone shift
    // new Date("2025-01-04") interprets as UTC, which shifts dates in western timezones
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  if (isLoading) {
    return <PlanViewSkeleton />;
  }

  return (
    <div className="space-y-6" role="region" aria-label="Meal Plan">
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <div>
            <h2 className="text-xl font-semibold" id="plan-heading">Meal Plan</h2>
            <p className="text-sm text-gray-600">Your 3-day rolling meal prep schedule</p>
          </div>
          {plans && plans.length > 1 && (
            <PlanHistorySelector
              plans={plans}
              selectedPlanId={currentPlan?.id ?? null}
              onSelectPlan={handleSelectPlan}
              onLoadMore={handleLoadMorePlans}
              hasMore={hasMorePlans}
              isLoadingMore={isLoadingMore}
            />
          )}
        </div>
        <div className="flex gap-2 flex-wrap justify-start sm:justify-end">
          {currentPlan && (
            <>
              <FeatureGate
                feature="export_pdf"
                fallback={
                  <DisabledFeatureButton
                    feature="export_pdf"
                    label="Export"
                    icon={<Download className="h-4 w-4 sm:mr-2" />}
                    size="sm"
                    showLabelOnMobile={false}
                  />
                }
              >
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" disabled={isExporting} aria-label="Export meal plan">
                      <Download className="h-4 w-4 sm:mr-2" />
                      <span className="hidden sm:inline">{isExporting ? 'Exporting...' : 'Export'}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Download as PDF</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => handleExportPdf(currentPlan.id, 'full')}>
                      Full Meal Plan
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportPdf(currentPlan.id, 'shopping')}>
                      Shopping List Only
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportPdf(currentPlan.id, 'catchup')}>
                      Catch-Up Summary
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </FeatureGate>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" disabled={isSendingEmail} aria-label="Email meal plan">
                    <Mail className="h-4 w-4 sm:mr-2" />
                    <span className="hidden sm:inline">{isSendingEmail ? 'Sending...' : 'Email'}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Send to Email</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => handleSendEmail(currentPlan.id, 'plan')}>
                    Full Meal Plan
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleSendEmail(currentPlan.id, 'adaptation')}>
                    Adaptation Summary
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <FeatureGate
                feature="fridge_bulk_import"
                fallback={
                  <DisabledFeatureButton
                    feature="fridge_bulk_import"
                    label="Stock Fridge"
                    icon={<ShoppingCart className="h-4 w-4 sm:mr-2" />}
                    size="sm"
                    showLabelOnMobile={false}
                  />
                }
              >
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsStockDialogOpen(true)}
                  aria-label="Stock fridge from meal plan"
                >
                  <ShoppingCart className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">Stock Fridge</span>
                </Button>
              </FeatureGate>
              <FeatureGate
                feature="plan_duplication"
                fallback={
                  <DisabledFeatureButton
                    feature="plan_duplication"
                    label="Duplicate"
                    icon={<Copy className="h-4 w-4 sm:mr-2" />}
                    size="sm"
                    showLabelOnMobile={false}
                  />
                }
              >
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDuplicateDialogOpen(true)}
                  aria-label="Duplicate meal plan"
                >
                  <Copy className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">Duplicate</span>
                </Button>
              </FeatureGate>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteDialogOpen(true)}
                aria-label="Delete meal plan"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Delete</span>
              </Button>
            </>
          )}
          <Button
            size="sm"
            onClick={() => setIsGenerateDialogOpen(true)}
            disabled={isGenerating}
            aria-label={isGenerating ? 'Generating meal plan' : currentPlan ? 'Regenerate meal plan' : 'Generate meal plan'}
            className="sm:text-sm"
          >
            {isGenerating ? 'Generating...' : currentPlan ? 'Regenerate' : 'Generate Plan'}
          </Button>
        </div>
      </div>

      {!currentPlan ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-500 mb-4">No meal plan yet. Generate one to get started!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {Object.entries(groupMealsByDate(currentPlan.meals))
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([date, meals]) => {
              const descriptionId = `day-desc-${date}`;
              const sortedMeals = [...meals].sort((a, b) => {
                const order = { breakfast: 0, lunch: 1, dinner: 2 };
                return (order[a.meal_type as keyof typeof order] || 0) - (order[b.meal_type as keyof typeof order] || 0);
              });
              const mealSummary = sortedMeals.map((m) => `${m.meal_type}: ${m.recipe.name}`).join(', ');
              const pendingCount = sortedMeals.filter((m) => m.prep_status === 'PENDING').length;
              const doneCount = sortedMeals.filter((m) => m.prep_status === 'DONE').length;
              return (
                <Card key={date} aria-describedby={descriptionId}>
                  {/* Visually hidden description for screen readers */}
                  <span id={descriptionId} className="sr-only">
                    {formatDate(date)}: {sortedMeals.length} meals planned. {mealSummary}.
                    {pendingCount > 0 && ` ${pendingCount} pending.`}
                    {doneCount > 0 && ` ${doneCount} completed.`}
                  </span>
                  <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2">
                    <CardTitle className="text-base sm:text-lg">{formatDate(date)}</CardTitle>
                    <Button
                      variant="ghost"
                      onClick={() => handleTimelineClick(date)}
                      aria-label={`View optimized prep timeline for ${formatDate(date)}`}
                      className="flex-shrink-0 min-h-[44px] min-w-[44px] px-3 touch-manipulation"
                    >
                      <Clock className="h-4 w-4 sm:mr-1.5" aria-hidden="true" />
                      <span className="hidden sm:inline">Timeline</span>
                    </Button>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {sortedMeals.map((meal) => {
                      const mealDescId = `meal-desc-${meal.id}`;
                      return (
                        <div
                          key={meal.id}
                          className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between p-3 bg-gray-50 rounded-lg"
                          role="article"
                          aria-describedby={mealDescId}
                        >
                          {/* Visually hidden meal description */}
                          <span id={mealDescId} className="sr-only">
                            {meal.meal_type} meal: {meal.recipe.name}, {meal.recipe.prep_time_minutes} minutes prep time,
                            {meal.recipe.servings && ` ${meal.recipe.servings} servings,`} status: {meal.prep_status.toLowerCase()}.
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium capitalize">{meal.meal_type}</span>
                              <Badge className={getStatusColor(meal.prep_status)} variant="secondary">
                                {meal.prep_status}
                              </Badge>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRecipeClick(meal.recipe)}
                              className="text-sm text-left hover:text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded truncate max-w-full block"
                              aria-label={`View recipe details for ${meal.recipe.name}`}
                            >
                              {meal.recipe.name}
                            </button>
                            <p className="text-xs text-gray-500">
                              {meal.recipe.prep_time_minutes} min prep
                              {meal.recipe.servings && ` • ${meal.recipe.servings} servings`}
                            </p>
                          </div>
                          {meal.prep_status === 'PENDING' && (
                            <div className="flex gap-2 sm:gap-3 flex-shrink-0" role="group" aria-label={`Actions for ${meal.meal_type} - ${meal.recipe.name}`}>
                              {isEnabled('meal_swap') && (
                                <Button
                                  variant="outline"
                                  aria-label={`Swap ${meal.meal_type} recipe`}
                                  onClick={() => handleSwapClick(meal)}
                                  className="min-h-[44px] min-w-[44px] px-3 touch-manipulation"
                                >
                                  <RefreshCw className="h-4 w-4 sm:mr-1.5" aria-hidden="true" />
                                  <span className="hidden sm:inline">Swap</span>
                                </Button>
                              )}
                              <Button
                                variant="outline"
                                aria-label={`Mark ${meal.meal_type} as done`}
                                onClick={() =>
                                  markPrepMutation.mutate({
                                    planId: currentPlan.id,
                                    date: meal.date,
                                    mealType: meal.meal_type,
                                    status: 'DONE',
                                  })
                                }
                                className="min-h-[44px] px-4 touch-manipulation"
                              >
                                Done
                              </Button>
                              <Button
                                variant="ghost"
                                aria-label={`Skip ${meal.meal_type}`}
                                onClick={() =>
                                  markPrepMutation.mutate({
                                    planId: currentPlan.id,
                                    date: meal.date,
                                    mealType: meal.meal_type,
                                    status: 'SKIPPED',
                                  })
                                }
                                className="min-h-[44px] px-4 touch-manipulation"
                              >
                                Skip
                              </Button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              );
            })}
        </div>
      )}

      <RecipeDetailDialog
        recipe={selectedRecipe}
        open={isRecipeDialogOpen}
        onOpenChange={setIsRecipeDialogOpen}
      />

      <PrepTimelineDialog
        planId={currentPlan?.id ?? null}
        date={selectedTimelineDate}
        open={isTimelineDialogOpen}
        onOpenChange={setIsTimelineDialogOpen}
      />

      <ConfirmationDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="Delete Meal Plan"
        description="Are you sure you want to delete this meal plan? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={() => currentPlan && handleDeletePlan(currentPlan.id)}
        isLoading={isDeleting}
        variant="destructive"
      />

      <MealSwapDialog
        planId={currentPlan?.id ?? ''}
        meal={swapMeal}
        open={isSwapDialogOpen}
        onOpenChange={setIsSwapDialogOpen}
        onSwap={handleSwapMeal}
      />

      <GeneratePlanDialog
        open={isGenerateDialogOpen}
        onOpenChange={setIsGenerateDialogOpen}
        onGenerate={async (startDate, days) => {
          await generateMutation.mutateAsync({ startDate, days });
        }}
        isLoading={isGenerating}
      />

      <DuplicatePlanDialog
        plan={currentPlan ?? null}
        open={isDuplicateDialogOpen}
        onOpenChange={setIsDuplicateDialogOpen}
        onDuplicate={handleDuplicatePlan}
        isLoading={isDuplicating}
      />

      <StockFridgeDialog
        plan={currentPlan ?? null}
        open={isStockDialogOpen}
        onOpenChange={setIsStockDialogOpen}
        onStock={async (items) => {
          await stockFridgeMutation.mutateAsync(items);
        }}
        isLoading={stockFridgeMutation.isPending}
      />
    </div>
  );
}
