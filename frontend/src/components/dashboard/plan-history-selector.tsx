'use client';

import { useState } from 'react';
import { MealPlan } from '@/types';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChevronDown, Calendar, Check } from 'lucide-react';

interface PlanHistorySelectorProps {
  plans: MealPlan[];
  selectedPlanId: string | null;
  onSelectPlan: (planId: string) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  isLoadingMore: boolean;
}

export function PlanHistorySelector({
  plans,
  selectedPlanId,
  onSelectPlan,
  onLoadMore,
  hasMore,
  isLoadingMore,
}: PlanHistorySelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedPlan = plans.find((p) => p.id === selectedPlanId);

  const formatDateRange = (startDate: string, endDate: string) => {
    // Parse as local time to avoid timezone shift
    // new Date("2025-01-04") interprets as UTC, which shifts dates in western timezones
    const [startYear, startMonth, startDay] = startDate.split('-').map(Number);
    const [endYear, endMonth, endDay] = endDate.split('-').map(Number);
    const start = new Date(startYear, startMonth - 1, startDay);
    const end = new Date(endYear, endMonth - 1, endDay);
    const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
    return `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
  };

  const formatCreatedAt = (createdAt: string) => {
    const date = new Date(createdAt);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const isCurrentPlan = (plan: MealPlan) => {
    return plans.indexOf(plan) === 0;
  };

  if (plans.length <= 1) {
    return null;
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="justify-between min-w-[200px]"
          aria-label="Select meal plan"
        >
          <span className="flex items-center gap-2 truncate">
            <Calendar className="h-4 w-4 flex-shrink-0" />
            {selectedPlan ? (
              <span className="truncate">
                {formatDateRange(selectedPlan.start_date, selectedPlan.end_date)}
              </span>
            ) : (
              'Select Plan'
            )}
          </span>
          <ChevronDown className="h-4 w-4 flex-shrink-0 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[280px]">
        <DropdownMenuLabel>Plan History</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="max-h-[300px] overflow-y-auto">
          {plans.map((plan) => (
            <DropdownMenuItem
              key={plan.id}
              onClick={() => {
                onSelectPlan(plan.id);
                setIsOpen(false);
              }}
              className="flex items-start gap-2 py-2"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    {formatDateRange(plan.start_date, plan.end_date)}
                  </span>
                  {isCurrentPlan(plan) && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">
                      Latest
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  Created {formatCreatedAt(plan.created_at)}
                </div>
                <div className="text-xs text-gray-500">
                  {plan.meals.length} meals &bull; {plan.diet_type}
                </div>
              </div>
              {selectedPlanId === plan.id && (
                <Check className="h-4 w-4 text-blue-600 flex-shrink-0" />
              )}
            </DropdownMenuItem>
          ))}
        </div>
        {hasMore && (
          <>
            <DropdownMenuSeparator />
            <div className="p-1">
              <Button
                variant="ghost"
                size="sm"
                className="w-full"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onLoadMore();
                }}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? 'Loading...' : 'Load More Plans'}
              </Button>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
