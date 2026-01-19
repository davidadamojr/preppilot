'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { plansApi, emailApi } from '@/lib/api';
import { planKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import { MealPlan, CatchUpSuggestions } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Clock, Leaf, CheckCircle2, CalendarDays, AlertTriangle, Mail } from 'lucide-react';
import { CatchUpViewSkeleton } from './skeletons';
import { useFeatureFlags, isFeatureDisabledError } from '@/hooks/use-feature-flags';
import { FEATURE_LABELS } from '@/components/ui/feature-gate';

export function CatchUpView() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const { user } = useAuth();
  const userId = user?.id;
  const { isEnabled } = useFeatureFlags();

  const { data: plans } = useQuery({
    queryKey: planKeys.list(userId),
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data as MealPlan[];
    },
    enabled: !!userId,
  });

  const currentPlan = plans?.[0];

  const { data: catchUpData, isLoading: isCatchUpLoading, refetch: refetchCatchUp } = useQuery({
    queryKey: planKeys.catchup(userId, currentPlan?.id),
    queryFn: async () => {
      if (!currentPlan) return null;
      const response = await plansApi.getCatchUp(currentPlan.id);
      return response.data as CatchUpSuggestions;
    },
    enabled: !!currentPlan && !!userId,
  });

  const adaptMutation = useMutation({
    mutationFn: async () => {
      if (!currentPlan) throw new Error('No plan');
      const response = await plansApi.adapt(currentPlan.id);
      return response.data;
    },
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: planKeys.all(userId) });

      // Snapshot the previous catch-up data
      const previousCatchUp = queryClient.getQueryData<CatchUpSuggestions>(planKeys.catchup(userId, currentPlan?.id));

      // Optimistically show "all caught up" state
      queryClient.setQueryData<CatchUpSuggestions>(planKeys.catchup(userId, currentPlan?.id), {
        missed_preps: [],
        expiring_items: [],
        pending_meals: [],
        needs_adaptation: false,
      });

      return { previousCatchUp };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.all(userId) });
      toast({
        title: 'Plan adapted successfully!',
        description: 'Your meal plan has been updated based on suggestions.',
      });
    },
    onError: (error, _variables, context) => {
      // Rollback to previous catch-up state
      if (context?.previousCatchUp) {
        queryClient.setQueryData(planKeys.catchup(userId, currentPlan?.id), context.previousCatchUp);
      }
      // Handle feature disabled error gracefully
      if (isFeatureDisabledError(error)) {
        toast({
          title: 'Feature unavailable',
          description: FEATURE_LABELS.plan_adaptation + ' is currently unavailable.',
        });
      } else {
        toast({
          title: 'Failed to adapt plan',
          description: 'Please try again.',
          variant: 'destructive',
        });
      }
    },
  });

  const handleSendEmail = async () => {
    if (!currentPlan) return;
    setIsSendingEmail(true);
    try {
      await emailApi.sendAdaptationEmail(currentPlan.id);
      toast({
        title: 'Email sent',
        description: 'Catch-up summary has been sent to your email.',
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

  if (!currentPlan) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-gray-500">Generate a meal plan first to see catch-up suggestions.</p>
        </CardContent>
      </Card>
    );
  }

  if (isCatchUpLoading) {
    return <CatchUpViewSkeleton />;
  }

  const hasIssues = catchUpData && (
    catchUpData.needs_adaptation ||
    catchUpData.expiring_items?.length > 0 ||
    catchUpData.missed_preps?.length > 0
  );

  return (
    <div className="space-y-6" role="region" aria-label="Catch-Up Assistant">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold">Catch-Up Assistant</h2>
          <p className="text-sm text-gray-600">Get back on track with adaptive suggestions</p>
        </div>
        <div className="flex gap-2" role="group" aria-label="Catch-up actions">
          <Button variant="outline" onClick={() => refetchCatchUp()} aria-label="Refresh catch-up suggestions">
            Refresh
          </Button>
          <Button
            variant="outline"
            onClick={handleSendEmail}
            disabled={isSendingEmail}
            aria-label={isSendingEmail ? 'Sending email' : 'Email catch-up summary'}
          >
            <Mail className="h-4 w-4 mr-2" />
            {isSendingEmail ? 'Sending...' : 'Email Summary'}
          </Button>
          {hasIssues && isEnabled('plan_adaptation') && (
            <Button
              onClick={() => adaptMutation.mutate()}
              disabled={adaptMutation.isPending}
              aria-label={adaptMutation.isPending ? 'Applying adaptations' : 'Apply adaptations to meal plan'}
            >
              {adaptMutation.isPending ? 'Adapting...' : 'Apply Adaptations'}
            </Button>
          )}
        </div>
      </div>

      {!hasIssues ? (
        <Card role="status" aria-label="No adaptations needed">
          <CardContent className="py-12 text-center">
            <div className="flex justify-center mb-2" aria-hidden="true">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <p className="text-gray-600">You&apos;re all caught up! No adaptations needed.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4" role="list" aria-label="Catch-up suggestions">
          {/* Missed Preps Section */}
          {catchUpData?.missed_preps && catchUpData.missed_preps.length > 0 && (
            <Card role="listitem" aria-describedby="missed-preps-desc">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" />
                  Missed Preparations
                </CardTitle>
                <CardDescription id="missed-preps-desc">
                  These prep sessions were missed and may need attention
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2" role="list" aria-label="Missed prep dates">
                  {catchUpData.missed_preps.map((missedDate: string, index: number) => (
                    <Badge key={index} variant="destructive" className="text-sm" role="listitem">
                      <Clock className="h-3 w-3 mr-1" aria-hidden="true" />
                      {missedDate}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Expiring Items Section */}
          {catchUpData?.expiring_items && catchUpData.expiring_items.length > 0 && (
            <Card role="listitem" aria-describedby="expiring-items-desc">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Leaf className="h-5 w-5 text-orange-500" aria-hidden="true" />
                  Expiring Soon
                </CardTitle>
                <CardDescription id="expiring-items-desc">
                  Use these ingredients first to minimize waste
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {catchUpData.expiring_items.map((item, index: number) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-orange-50 rounded-lg"
                    role="article"
                    aria-label={`${item.name} expires in ${item.days_remaining} days`}
                  >
                    <div className="flex items-center gap-3">
                      <Leaf className="h-4 w-4 text-orange-600" aria-hidden="true" />
                      <div>
                        <span className="font-medium">{item.name}</span>
                        <span className="text-sm text-gray-500 ml-2">({item.quantity})</span>
                      </div>
                    </div>
                    <Badge
                      variant={item.days_remaining <= 1 ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
                      {item.days_remaining === 0
                        ? 'Expires today'
                        : item.days_remaining === 1
                        ? '1 day left'
                        : `${item.days_remaining} days left`}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Pending Meals Section */}
          {catchUpData?.pending_meals && catchUpData.pending_meals.length > 0 && (
            <Card role="listitem" aria-describedby="pending-meals-desc">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-blue-500" aria-hidden="true" />
                  Upcoming Meals
                </CardTitle>
                <CardDescription id="pending-meals-desc">
                  Meals that still need to be prepared
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {catchUpData.pending_meals.slice(0, 5).map((meal, index: number) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    role="article"
                    aria-label={`${meal.recipe} for ${meal.meal_type} on ${meal.date}`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{meal.recipe}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs capitalize">
                        {meal.meal_type}
                      </Badge>
                      <span className="text-sm text-gray-500">{meal.date}</span>
                    </div>
                  </div>
                ))}
                {catchUpData.pending_meals.length > 5 && (
                  <p className="text-sm text-gray-500 text-center pt-2">
                    And {catchUpData.pending_meals.length - 5} more meals...
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
