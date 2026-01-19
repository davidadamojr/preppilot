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
import { CalendarPlus } from 'lucide-react';

interface GeneratePlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (startDate: string, days: number) => Promise<void>;
  isLoading?: boolean;
}

function formatDateForInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function calculateEndDate(startDate: string, days: number): string {
  const [year, month, day] = startDate.split('-').map(Number);
  const start = new Date(year, month - 1, day);
  start.setDate(start.getDate() + days - 1);
  return formatDateForInput(start);
}

const DEFAULT_DAYS = 3;
const MIN_DAYS = 1;
const MAX_DAYS = 7;

export function GeneratePlanDialog({
  open,
  onOpenChange,
  onGenerate,
  isLoading = false,
}: GeneratePlanDialogProps) {
  const [startDate, setStartDate] = useState(getDefaultStartDate);
  const [days, setDays] = useState(DEFAULT_DAYS);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onGenerate(startDate, days);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      // Reset to defaults when opening
      setStartDate(getDefaultStartDate());
      setDays(DEFAULT_DAYS);
    }
    onOpenChange(newOpen);
  };

  const endDate = calculateEndDate(startDate, days);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarPlus className="h-5 w-5" />
            Generate Meal Plan
          </DialogTitle>
          <DialogDescription>
            Choose when your meal plan should start and how many days to plan for.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="start-date">Start Date</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min={getMinDate()}
                max={getMaxDate()}
                required
                aria-describedby="start-date-hint"
              />
              <p id="start-date-hint" className="text-xs text-gray-500">
                Must be today or within the next 30 days
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="days">Number of Days</Label>
              <Input
                id="days"
                type="number"
                value={days}
                onChange={(e) => {
                  const value = parseInt(e.target.value, 10);
                  if (!isNaN(value)) {
                    setDays(Math.min(MAX_DAYS, Math.max(MIN_DAYS, value)));
                  }
                }}
                min={MIN_DAYS}
                max={MAX_DAYS}
                required
                aria-describedby="days-hint"
              />
              <p id="days-hint" className="text-xs text-gray-500">
                Between {MIN_DAYS} and {MAX_DAYS} days
              </p>
            </div>

            <div className="bg-blue-50 rounded-lg p-3 text-sm">
              <p className="font-medium text-blue-700">Plan Summary</p>
              <p className="text-blue-600">
                {formatDisplayDate(startDate)} – {formatDisplayDate(endDate)}
              </p>
              <p className="text-blue-500">
                {days} day{days !== 1 ? 's' : ''} • {days * 3} meals
              </p>
            </div>
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
              {isLoading ? 'Generating...' : 'Generate Plan'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
