'use client';

import { useQuery } from '@tanstack/react-query';
import { plansApi } from '@/lib/api';
import { planKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import { OptimizedPrepTimeline, PrepStep, CookingPhase } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { LoadingState } from '@/components/ui/spinner';
import {
  Clock,
  Timer,
  Sparkles,
  ChefHat,
  Flame,
  Utensils,
  Coffee,
} from 'lucide-react';

interface PrepTimelineDialogProps {
  planId: string | null;
  date: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PrepTimelineDialog({
  planId,
  date,
  open,
  onOpenChange,
}: PrepTimelineDialogProps) {
  const { user } = useAuth();
  const userId = user?.id;

  const { data: timeline, isLoading, error } = useQuery<OptimizedPrepTimeline | null>({
    queryKey: planKeys.prepTimeline(userId, planId ?? '', date ?? ''),
    queryFn: async () => {
      if (!planId || !date) return null;
      const response = await plansApi.getPrepTimeline(planId, date);
      return response.data as OptimizedPrepTimeline;
    },
    enabled: open && !!planId && !!date && !!userId,
  });

  const formatDate = (dateStr: string) => {
    // Parse as local time to avoid timezone shift
    // new Date("2025-01-04") interprets as UTC, which shifts dates in western timezones
    const [year, month, day] = dateStr.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMins = minutes % 60;
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
  };

  const getStepTypeColor = (step: PrepStep) => {
    if (step.can_batch) {
      return 'bg-purple-100 text-purple-800';
    }
    if (step.is_passive) {
      return 'bg-amber-100 text-amber-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  const getPhaseIcon = (phase: CookingPhase | null) => {
    switch (phase) {
      case 'prep':
        return <Utensils className="h-4 w-4" />;
      case 'cooking':
        return <Flame className="h-4 w-4" />;
      case 'finishing':
        return <Coffee className="h-4 w-4" />;
      default:
        return <ChefHat className="h-4 w-4" />;
    }
  };

  const getPhaseLabel = (phase: CookingPhase | null) => {
    switch (phase) {
      case 'prep':
        return 'Prep';
      case 'cooking':
        return 'Cooking';
      case 'finishing':
        return 'Finishing';
      default:
        return '';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" aria-describedby="timeline-description">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Optimized Prep Timeline
          </DialogTitle>
          <DialogDescription id="timeline-description">
            {date ? `Batched cooking schedule for ${formatDate(date)}` : 'Loading...'}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <LoadingState message="Optimizing your prep schedule..." />
        ) : error ? (
          <div className="py-8 text-center text-red-600">
            Failed to load prep timeline. Please try again.
          </div>
        ) : !timeline || timeline.steps.length === 0 ? (
          <div className="py-8 text-center text-gray-500">
            No meals scheduled for this date.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center gap-1 text-blue-600 mb-1">
                  <Timer className="h-4 w-4" />
                  <span className="text-xs font-medium">Total Time</span>
                </div>
                <p className="text-xl font-bold text-blue-700">
                  {formatDuration(timeline.total_time_minutes)}
                </p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <div className="flex items-center justify-center gap-1 text-green-600 mb-1">
                  <Sparkles className="h-4 w-4" />
                  <span className="text-xs font-medium">Time Saved</span>
                </div>
                <p className="text-xl font-bold text-green-700">
                  {formatDuration(timeline.batched_savings_minutes)}
                </p>
              </div>
            </div>

            {/* Savings Message */}
            {timeline.batched_savings_minutes > 0 && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                <Sparkles className="h-4 w-4 inline mr-2" />
                Similar tasks have been batched together, saving you{' '}
                <strong>{formatDuration(timeline.batched_savings_minutes)}</strong> of prep time!
              </div>
            )}

            {/* Timeline Steps */}
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900">Prep Steps</h3>
              <ol
                className="space-y-2"
                role="list"
                aria-label="Preparation steps"
              >
                {timeline.steps.map((step: PrepStep) => (
                  <li
                    key={step.step_number}
                    className="p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium"
                        aria-hidden="true"
                      >
                        {step.step_number}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-gray-900">{step.action}</p>
                        {step.source_recipes && step.source_recipes.length > 0 && (
                          <div className="flex items-center gap-1 mt-1 text-xs text-blue-600">
                            <ChefHat className="h-3 w-3" />
                            <span>
                              {step.source_recipes.length === 1
                                ? step.source_recipes[0]
                                : step.source_recipes.join(' + ')}
                            </span>
                          </div>
                        )}
                        <div className="flex flex-wrap items-center gap-2 mt-1">
                          <Badge
                            variant="secondary"
                            className={getStepTypeColor(step)}
                          >
                            {step.can_batch ? 'Batched' : step.is_passive ? 'Passive' : 'Active'}
                          </Badge>
                          {step.phase && (
                            <Badge variant="outline" className="text-xs">
                              {getPhaseIcon(step.phase)}
                              <span className="ml-1">{getPhaseLabel(step.phase)}</span>
                            </Badge>
                          )}
                          {step.ingredient && (
                            <span className="text-xs text-gray-500">
                              {step.ingredient}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex-shrink-0 text-sm text-gray-500 whitespace-nowrap">
                        {formatDuration(step.duration_minutes)}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
