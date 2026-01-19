'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { MealPlan } from '@/types';
import { Copy } from 'lucide-react';

interface DuplicatePlanDialogProps {
  plan: MealPlan | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDuplicate: (startDate: string) => Promise<void>;
  isLoading?: boolean;
}

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}

function getDefaultStartDate(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return formatDateForInput(tomorrow);
}

function getMinDate(): string {
  return formatDateForInput(new Date());
}

function getMaxDate(): string {
  const maxDate = new Date();
  maxDate.setDate(maxDate.getDate() + 30);
  return formatDateForInput(maxDate);
}

function formatDisplayDate(dateStr: string): string {
  // Parse as local time to avoid timezone shift
  // new Date("2025-01-04") interprets as UTC, which shifts dates in western timezones
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

export function DuplicatePlanDialog({
  plan,
  open,
  onOpenChange,
  onDuplicate,
  isLoading = false,
}: DuplicatePlanDialogProps) {
  const [startDate, setStartDate] = useState(getDefaultStartDate);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onDuplicate(startDate);
  };

  // Calculate the duration of the original plan
  // Parse dates as local time to avoid timezone issues
  const planDuration = plan
    ? (() => {
        const [startYear, startMonth, startDay] = plan.start_date.split('-').map(Number);
        const [endYear, endMonth, endDay] = plan.end_date.split('-').map(Number);
        const startDate = new Date(startYear, startMonth - 1, startDay);
        const endDate = new Date(endYear, endMonth - 1, endDay);
        return Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      })()
    : 0;

  // Calculate new end date based on selected start date
  const newEndDate = (() => {
    if (!plan) return '';
    // Parse as local time to avoid timezone shift
    const [year, month, day] = startDate.split('-').map(Number);
    const start = new Date(year, month - 1, day);
    start.setDate(start.getDate() + planDuration - 1);
    return formatDateForInput(start);
  })();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Duplicate Meal Plan
          </DialogTitle>
          <DialogDescription>
            Create a copy of this meal plan with a new start date. All meal recipes will be
            preserved, and prep statuses will be reset to pending.
          </DialogDescription>
        </DialogHeader>

        {plan && (
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="bg-gray-50 rounded-lg p-3 text-sm">
                <p className="font-medium text-gray-700">Original Plan</p>
                <p className="text-gray-600">
                  {formatDisplayDate(plan.start_date)} – {formatDisplayDate(plan.end_date)}
                </p>
                <p className="text-gray-500">
                  {planDuration} day{planDuration !== 1 ? 's' : ''} • {plan.meals.length} meals
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="start-date">New Start Date</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  min={getMinDate()}
                  max={getMaxDate()}
                  required
                  aria-describedby="date-hint"
                />
                <p id="date-hint" className="text-xs text-gray-500">
                  Must be today or within the next 30 days
                </p>
              </div>

              {newEndDate && (
                <div className="bg-blue-50 rounded-lg p-3 text-sm">
                  <p className="font-medium text-blue-700">New Plan Dates</p>
                  <p className="text-blue-600">
                    {formatDisplayDate(startDate)} – {formatDisplayDate(newEndDate)}
                  </p>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Duplicating...' : 'Duplicate Plan'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
