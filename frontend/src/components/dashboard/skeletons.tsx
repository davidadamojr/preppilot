'use client';

import {
  Skeleton,
  SkeletonBadge,
  SkeletonButton,
  SkeletonProgress,
  SkeletonInput,
} from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

/**
 * Skeleton for a single meal row in the plan view.
 */
function MealRowSkeleton() {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <div className="flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-20" /> {/* Meal type */}
          <SkeletonBadge /> {/* Status badge */}
        </div>
        <Skeleton className="h-4 w-48" /> {/* Recipe name */}
        <Skeleton className="h-3 w-32" /> {/* Prep time + servings */}
      </div>
      <div className="flex gap-2">
        <SkeletonButton size="sm" />
        <SkeletonButton size="sm" />
        <SkeletonButton size="sm" className="w-12" />
      </div>
    </div>
  );
}

/**
 * Skeleton for a single day card in the plan view.
 */
function DayCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <Skeleton className="h-6 w-32" /> {/* Date */}
        <SkeletonButton size="sm" className="w-24" /> {/* Timeline button */}
      </CardHeader>
      <CardContent className="space-y-3">
        <MealRowSkeleton />
        <MealRowSkeleton />
        <MealRowSkeleton />
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for the meal plan view loading state.
 * Matches the structure: header + 3 day cards (3-day rolling schedule).
 */
export function PlanViewSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading meal plans">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center">
        <div className="space-y-2">
          <Skeleton className="h-7 w-32" /> {/* "Meal Plan" title */}
          <Skeleton className="h-4 w-64" /> {/* Subtitle */}
        </div>
        <div className="flex gap-2 flex-wrap">
          <SkeletonButton /> {/* Export */}
          <SkeletonButton /> {/* Email */}
          <SkeletonButton /> {/* Duplicate */}
          <SkeletonButton /> {/* Delete */}
          <SkeletonButton className="w-32" /> {/* Generate Plan */}
        </div>
      </div>

      {/* Day cards */}
      <div className="space-y-4">
        <DayCardSkeleton />
        <DayCardSkeleton />
        <DayCardSkeleton />
      </div>
    </div>
  );
}

/**
 * Skeleton for a single fridge item card.
 */
function FridgeItemSkeleton() {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-32" /> {/* Ingredient name */}
              <SkeletonBadge className="w-20" /> {/* Urgency badge */}
            </div>
            <Skeleton className="h-4 w-40" /> {/* Quantity + days */}
            <div className="flex items-center gap-2">
              <SkeletonProgress className="flex-1" />
              <Skeleton className="h-3 w-10" /> {/* Percentage */}
            </div>
          </div>
          <div className="flex gap-1">
            <SkeletonButton size="sm" className="w-8" /> {/* Edit */}
            <SkeletonButton size="sm" className="w-16" /> {/* Remove */}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for the fridge view loading state.
 * Matches the structure: header, alert (optional), add form, item list.
 */
export function FridgeViewSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading fridge inventory">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" /> {/* "Fridge Inventory" */}
          <Skeleton className="h-4 w-56" /> {/* Subtitle */}
        </div>
        <SkeletonButton size="sm" className="w-24" /> {/* Clear All */}
      </div>

      {/* Add Ingredient Form */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <Skeleton className="h-6 w-32" /> {/* "Add Ingredient" */}
          <SkeletonButton size="sm" className="w-28" /> {/* Bulk Import */}
        </CardHeader>
        <CardContent>
          <div className="flex gap-3 items-end">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-12" /> {/* Label */}
              <SkeletonInput />
            </div>
            <div className="w-32 space-y-2">
              <Skeleton className="h-4 w-16" /> {/* Label */}
              <SkeletonInput />
            </div>
            <div className="w-24 space-y-2">
              <Skeleton className="h-4 w-20" /> {/* Label */}
              <SkeletonInput />
            </div>
            <SkeletonButton />
          </div>
        </CardContent>
      </Card>

      {/* Fridge Items */}
      <div className="grid gap-3">
        <FridgeItemSkeleton />
        <FridgeItemSkeleton />
        <FridgeItemSkeleton />
        <FridgeItemSkeleton />
        <FridgeItemSkeleton />
      </div>
    </div>
  );
}

/**
 * Skeleton for a catch-up suggestion section.
 */
function CatchUpSectionSkeleton({ badges = false }: { badges?: boolean }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" /> {/* Icon */}
          <Skeleton className="h-6 w-40" /> {/* Title */}
        </div>
        <Skeleton className="h-4 w-64" /> {/* Description */}
      </CardHeader>
      <CardContent>
        {badges ? (
          <div className="flex flex-wrap gap-2">
            <SkeletonBadge className="w-24" />
            <SkeletonBadge className="w-20" />
            <SkeletonBadge className="w-28" />
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-4 rounded" />
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-16" />
              </div>
              <SkeletonBadge className="w-20" />
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-4 rounded" />
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-4 w-12" />
              </div>
              <SkeletonBadge className="w-16" />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for the catch-up view loading state.
 */
export function CatchUpViewSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading catch-up suggestions">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="space-y-2">
          <Skeleton className="h-7 w-44" /> {/* "Catch-Up Assistant" */}
          <Skeleton className="h-4 w-64" /> {/* Subtitle */}
        </div>
        <div className="flex gap-2">
          <SkeletonButton /> {/* Refresh */}
          <SkeletonButton className="w-32" /> {/* Email Summary */}
          <SkeletonButton className="w-36" /> {/* Apply Adaptations */}
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-4">
        <CatchUpSectionSkeleton badges /> {/* Missed preps */}
        <CatchUpSectionSkeleton /> {/* Expiring items */}
        <CatchUpSectionSkeleton /> {/* Pending meals */}
      </div>
    </div>
  );
}

/**
 * Skeleton for the dietary exclusions list only (used inline in settings).
 */
export function ExclusionsListSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading dietary exclusions">
      {/* Scrollable list skeleton */}
      <div className="max-h-64 overflow-y-auto border rounded-md p-3 space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center space-x-2 p-2">
            <Skeleton className="h-4 w-4 rounded" /> {/* Checkbox */}
            <Skeleton className="h-4 w-32" /> {/* Label */}
          </div>
        ))}
      </div>
      {/* Action buttons */}
      <div className="flex gap-3 pt-2">
        <SkeletonButton className="w-28" /> {/* Save Changes */}
      </div>
    </div>
  );
}

/**
 * Skeleton for the profile card in settings.
 */
function ProfileCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <Skeleton className="h-6 w-16" /> {/* "Profile" */}
          <Skeleton className="h-4 w-40" /> {/* Description */}
        </div>
        <SkeletonButton size="sm" className="w-24" /> {/* Edit Profile */}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {/* Email */}
          <div className="space-y-1">
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-40" />
          </div>
          {/* Full Name */}
          <div className="space-y-1">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-32" />
          </div>
          {/* Diet Type */}
          <div className="space-y-1">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-28" />
          </div>
          {/* Account Status */}
          <div className="space-y-1">
            <Skeleton className="h-4 w-28" />
            <SkeletonBadge />
          </div>
          {/* Member Since */}
          <div className="space-y-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-36" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for the dietary exclusions card.
 */
function ExclusionsCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" /> {/* "Dietary Exclusions" */}
        <Skeleton className="h-4 w-80" /> {/* Description */}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scrollable list */}
        <div className="border rounded-md p-3 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center space-x-2 p-2">
              <Skeleton className="h-4 w-4 rounded" /> {/* Checkbox */}
              <Skeleton className="h-4 w-32" /> {/* Label */}
            </div>
          ))}
        </div>
        {/* Action buttons */}
        <div className="flex gap-3 pt-2">
          <SkeletonButton className="w-28" /> {/* Save Changes */}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for the password card.
 */
function PasswordCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <Skeleton className="h-6 w-20" /> {/* "Password" */}
          <Skeleton className="h-4 w-48" /> {/* Description */}
        </div>
        <SkeletonButton size="sm" className="w-36" /> {/* Change Password */}
      </CardHeader>
    </Card>
  );
}

/**
 * Skeleton for the settings view loading state.
 */
export function SettingsViewSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading settings">
      <ProfileCardSkeleton />
      <ExclusionsCardSkeleton />
      <PasswordCardSkeleton />
      {/* Danger zone card - simple skeleton */}
      <Card className="border-red-200">
        <CardHeader>
          <Skeleton className="h-6 w-28" /> {/* "Danger Zone" */}
          <Skeleton className="h-4 w-72" /> {/* Description */}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-64" />
            </div>
            <SkeletonButton size="sm" className="w-32 bg-red-100" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Skeleton for a single recipe card.
 */
function RecipeCardSkeleton() {
  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer">
      <CardContent className="p-4 space-y-3">
        <div className="flex justify-between items-start">
          <Skeleton className="h-5 w-40" /> {/* Recipe name */}
          <SkeletonBadge /> {/* Meal type badge */}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-16" />
          </div>
          <div className="flex items-center gap-1">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        <div className="flex flex-wrap gap-1">
          <SkeletonBadge className="w-20" />
          <SkeletonBadge className="w-16" />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton for just the recipe grid (used inline when filters are visible).
 */
export function RecipeGridSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading recipes">
      {/* Recipe grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <RecipeCardSkeleton key={i} />
        ))}
      </div>

      {/* Pagination */}
      <div className="flex justify-center gap-2">
        <SkeletonButton size="sm" />
        <Skeleton className="h-8 w-20" />
        <SkeletonButton size="sm" />
      </div>
    </div>
  );
}

/**
 * Skeleton for the recipe browser loading state (full page).
 */
export function RecipeBrowserSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading recipes">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-7 w-36" /> {/* "Recipe Browser" */}
        <Skeleton className="h-4 w-72" /> {/* Subtitle */}
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4 space-y-4">
          {/* Search form */}
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <SkeletonInput />
            </div>
            <SkeletonButton />
          </div>
          {/* Filters */}
          <div className="flex gap-4">
            <div className="w-48 space-y-1">
              <Skeleton className="h-4 w-20" />
              <SkeletonInput />
            </div>
            <div className="w-48 space-y-1">
              <Skeleton className="h-4 w-16" />
              <SkeletonInput />
            </div>
          </div>
        </CardContent>
      </Card>

      <RecipeGridSkeleton />
    </div>
  );
}

/**
 * Skeleton for the dashboard page initial loading state.
 * Shows header + tabs + plan view skeleton (default tab).
 */
export function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50" role="status" aria-label="Loading dashboard">
      {/* Header skeleton */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <Skeleton className="h-8 w-28" /> {/* PrepPilot logo */}
            <SkeletonButton size="sm" className="w-32" /> {/* Browse Recipes */}
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <SkeletonBadge className="w-24" /> {/* Diet type */}
              <SkeletonBadge className="w-20" /> {/* Exclusions */}
            </div>
            <div className="flex flex-col items-end gap-1">
              <Skeleton className="h-4 w-24" /> {/* Name */}
              <Skeleton className="h-4 w-32" /> {/* Email */}
            </div>
            <SkeletonButton size="sm" className="w-20" /> {/* Sign out */}
          </div>
        </div>
      </header>

      {/* Main content skeleton */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Tabs skeleton */}
        <div className="mb-6">
          <div className="grid w-full grid-cols-4 max-w-lg h-10 rounded-md bg-gray-100 p-1">
            <Skeleton className="h-8 rounded-md" />
            <Skeleton className="h-8 rounded-md bg-transparent" />
            <Skeleton className="h-8 rounded-md bg-transparent" />
            <Skeleton className="h-8 rounded-md bg-transparent" />
          </div>
        </div>

        {/* Plan view skeleton (default tab) */}
        <PlanViewSkeleton />
      </main>
    </div>
  );
}
