'use client';

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth-context';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { PlanView } from '@/components/dashboard/plan-view';
import { FridgeView } from '@/components/dashboard/fridge-view';
import { CatchUpView } from '@/components/dashboard/catch-up-view';
import { SettingsView } from '@/components/dashboard/settings-view';
import {
  PlanErrorBoundary,
  FridgeErrorBoundary,
  CatchUpErrorBoundary,
  SettingsErrorBoundary,
} from '@/components/ui/error-boundary';
import { DashboardSkeleton } from '@/components/dashboard/skeletons';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { ChefHat } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { DIET_TYPE_LABELS } from '@/lib/utils';

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  // Handle logout with cache clearing to prevent data leakage between users
  const handleLogout = useCallback(() => {
    queryClient.clear();
    logout();
  }, [queryClient, logout]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:py-4">
          {/* Mobile: stacked layout, Desktop: side-by-side */}
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center">
            {/* Logo and navigation */}
            <div className="flex items-center justify-between sm:justify-start gap-3 sm:gap-6">
              <h1 className="text-xl sm:text-2xl font-bold">PrepPilot</h1>
              <Link href="/recipes">
                <Button variant="ghost" size="sm">
                  <ChefHat className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">Browse Recipes</span>
                </Button>
              </Link>
            </div>
            {/* User info and actions */}
            <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-4">
              {/* Diet badges - hide on very small screens */}
              <div className="hidden xs:flex items-center gap-1 sm:gap-2">
                <Badge variant="secondary" className="text-xs">
                  {DIET_TYPE_LABELS[user.diet_type] || user.diet_type}
                </Badge>
                {user.dietary_exclusions && user.dietary_exclusions.length > 0 && (
                  <Badge variant="outline" className="text-xs hidden sm:inline-flex">
                    {user.dietary_exclusions.length} exclusion{user.dietary_exclusions.length !== 1 ? 's' : ''}
                  </Badge>
                )}
              </div>
              {/* User name/email */}
              <div className="flex flex-col items-end min-w-0">
                {user.full_name && (
                  <span className="text-sm font-medium text-gray-900 truncate max-w-[150px] sm:max-w-none">{user.full_name}</span>
                )}
                <span className="text-xs sm:text-sm text-gray-600 truncate max-w-[150px] sm:max-w-none">{user.email}</span>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" className="whitespace-nowrap">
                    Sign out
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Sign out?</AlertDialogTitle>
                    <AlertDialogDescription>
                      Are you sure you want to sign out? You&apos;ll need to log in again to access your meal plans.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleLogout}>Sign out</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </div>
      </header>

      <main id="main-content" className="max-w-7xl mx-auto px-4 py-6">
        <Tabs defaultValue="plan" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 sm:grid-cols-4 max-w-sm sm:max-w-lg">
            <TabsTrigger value="plan">Plan</TabsTrigger>
            <TabsTrigger value="fridge">Fridge</TabsTrigger>
            <TabsTrigger value="catchup">Catch-Up</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="plan">
            <PlanErrorBoundary>
              <PlanView />
            </PlanErrorBoundary>
          </TabsContent>

          <TabsContent value="fridge">
            <FridgeErrorBoundary>
              <FridgeView />
            </FridgeErrorBoundary>
          </TabsContent>

          <TabsContent value="catchup">
            <CatchUpErrorBoundary>
              <CatchUpView />
            </CatchUpErrorBoundary>
          </TabsContent>

          <TabsContent value="settings">
            <SettingsErrorBoundary>
              <SettingsView />
            </SettingsErrorBoundary>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
