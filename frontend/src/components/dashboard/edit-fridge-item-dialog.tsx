'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FridgeItem } from '@/types';

interface EditFridgeItemDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: FridgeItem | null;
  onSave: (id: string, updates: { quantity?: string; days_remaining?: number }) => void;
  isLoading?: boolean;
}

export function EditFridgeItemDialog({
  open,
  onOpenChange,
  item,
  onSave,
  isLoading = false,
}: EditFridgeItemDialogProps) {
  const [quantity, setQuantity] = useState('');
  const [daysRemaining, setDaysRemaining] = useState('');

  // Reset form when item changes
  useEffect(() => {
    if (item) {
      setQuantity(item.quantity);
      setDaysRemaining(String(item.days_remaining));
    }
  }, [item]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!item) return;

    const updates: { quantity?: string; days_remaining?: number } = {};

    // Only include fields that changed
    if (quantity !== item.quantity) {
      updates.quantity = quantity;
    }
    const newDays = parseInt(daysRemaining, 10);
    if (!isNaN(newDays) && newDays !== item.days_remaining) {
      updates.days_remaining = newDays;
    }

    // Only save if something changed
    if (Object.keys(updates).length > 0) {
      onSave(item.id, updates);
    } else {
      onOpenChange(false);
    }
  };

  const isValid = quantity.trim().length > 0 && daysRemaining.trim().length > 0 && parseInt(daysRemaining, 10) >= 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit {item?.ingredient_name}</DialogTitle>
          <DialogDescription>Update the quantity or freshness of this item.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-quantity">Quantity</Label>
              <Input
                id="edit-quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="e.g., 2 lbs, 500g"
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-days">Days Remaining</Label>
              <Input
                id="edit-days"
                type="number"
                min="0"
                max="365"
                value={daysRemaining}
                onChange={(e) => setDaysRemaining(e.target.value)}
                disabled={isLoading}
              />
              <p className="text-xs text-muted-foreground">Set to 0 to mark as expired</p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !isValid}>
              {isLoading ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
