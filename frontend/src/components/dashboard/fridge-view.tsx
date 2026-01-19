'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fridgeApi, emailApi } from '@/lib/api';
import { fridgeKeys } from '@/lib/query-keys';
import { useAuth } from '@/lib/auth-context';
import { FridgeItem } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { AlertTriangle, Mail, Upload, Trash2, Pencil, ChefHat } from 'lucide-react';
import { FridgeViewSkeleton } from './skeletons';
import Link from 'next/link';
import { BulkFridgeImportDialog } from './bulk-fridge-import-dialog';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { EditFridgeItemDialog } from './edit-fridge-item-dialog';
import { FeatureGate, DisabledFeatureButton, FEATURE_LABELS } from '@/components/ui/feature-gate';
import { isFeatureDisabledError } from '@/hooks/use-feature-flags';

export function FridgeView() {
  const [newItem, setNewItem] = useState({ name: '', quantity: '', days: '7' });
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [isBulkImportOpen, setIsBulkImportOpen] = useState(false);
  const [isBulkImporting, setIsBulkImporting] = useState(false);
  const [isClearDialogOpen, setIsClearDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<FridgeItem | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();
  const userId = user?.id;

  // Poll every 5 minutes to keep freshness data in sync with backend decay job
  // Only polls when window is focused to save resources
  const FRESHNESS_POLL_INTERVAL = 5 * 60 * 1000; // 5 minutes

  const { data: fridgeItems, isLoading } = useQuery({
    queryKey: fridgeKeys.list(userId),
    queryFn: async () => {
      const response = await fridgeApi.get();
      return response.data.items as FridgeItem[];
    },
    enabled: !!userId,
    refetchInterval: FRESHNESS_POLL_INTERVAL,
    refetchIntervalInBackground: false, // Only refetch when window is focused
  });

  // Fetch expiring items from server instead of filtering client-side
  const { data: expiringItems = [] } = useQuery({
    queryKey: fridgeKeys.expiring(userId, 2),
    queryFn: async () => {
      const response = await fridgeApi.getExpiring(2);
      return response.data as FridgeItem[];
    },
    // Only fetch when we have fridge items loaded and user is logged in
    enabled: !isLoading && !!userId,
    refetchInterval: FRESHNESS_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });

  const addItemMutation = useMutation({
    mutationFn: async (item: { name: string; quantity: string; days: number }) => {
      return fridgeApi.addItem(item.name, item.quantity, item.days);
    },
    onMutate: async (item) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: fridgeKeys.all(userId) });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData<FridgeItem[]>(fridgeKeys.list(userId));

      // Optimistically add the new item
      const optimisticItem: FridgeItem = {
        id: `temp-${Date.now()}`, // Temporary ID
        ingredient_name: item.name,
        quantity: item.quantity,
        days_remaining: item.days,
        original_freshness_days: item.days,
        added_date: new Date().toISOString(),
        freshness_percentage: 100,
      };

      queryClient.setQueryData<FridgeItem[]>(fridgeKeys.list(userId), (old) => {
        return old ? [...old, optimisticItem] : [optimisticItem];
      });

      // Clear form immediately for better UX
      const previousFormState = { ...newItem };
      setNewItem({ name: '', quantity: '', days: '7' });

      return { previousItems, previousFormState };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
      toast({
        title: 'Item added to fridge',
        description: 'Your ingredient has been added to inventory.',
      });
    },
    onError: (_error, _variables, context) => {
      // Rollback to previous state
      if (context?.previousItems) {
        queryClient.setQueryData(fridgeKeys.list(userId), context.previousItems);
      }
      // Restore form state
      if (context?.previousFormState) {
        setNewItem(context.previousFormState);
      }
      toast({
        title: 'Failed to add item',
        description: 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const removeItemMutation = useMutation({
    mutationFn: async (id: string) => {
      return fridgeApi.removeItem(id);
    },
    onMutate: async (id: string) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: fridgeKeys.all(userId) });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData<FridgeItem[]>(fridgeKeys.list(userId));

      // Optimistically remove the item
      queryClient.setQueryData<FridgeItem[]>(fridgeKeys.list(userId), (old) => {
        return old ? old.filter((item) => item.id !== id) : [];
      });

      return { previousItems };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
    },
    onError: (_error, _variables, context) => {
      // Rollback to previous state
      if (context?.previousItems) {
        queryClient.setQueryData(fridgeKeys.list(userId), context.previousItems);
      }
      toast({
        title: 'Failed to remove item',
        description: 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const clearFridgeMutation = useMutation({
    mutationFn: async () => {
      return fridgeApi.clear();
    },
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: fridgeKeys.all(userId) });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData<FridgeItem[]>(fridgeKeys.list(userId));

      // Optimistically clear all items
      queryClient.setQueryData<FridgeItem[]>(fridgeKeys.list(userId), []);

      // Close dialog immediately for better UX
      setIsClearDialogOpen(false);

      return { previousItems };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
      toast({
        title: 'Fridge cleared',
        description: 'All items have been removed from your fridge.',
      });
    },
    onError: (_error, _variables, context) => {
      // Rollback to previous state
      if (context?.previousItems) {
        queryClient.setQueryData(fridgeKeys.list(userId), context.previousItems);
      }
      // Reopen the dialog on error so user knows operation failed
      setIsClearDialogOpen(true);
      toast({
        title: 'Failed to clear fridge',
        description: 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const updateItemMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: { quantity?: string; days_remaining?: number } }) => {
      return fridgeApi.updateItem(id, updates);
    },
    onMutate: async ({ id, updates }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: fridgeKeys.all(userId) });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData<FridgeItem[]>(fridgeKeys.list(userId));

      // Optimistically update the item
      queryClient.setQueryData<FridgeItem[]>(fridgeKeys.list(userId), (old) => {
        if (!old) return old;
        return old.map((item) => {
          if (item.id !== id) return item;

          const updatedItem = { ...item };
          if (updates.quantity !== undefined) {
            updatedItem.quantity = updates.quantity;
          }
          if (updates.days_remaining !== undefined) {
            updatedItem.days_remaining = updates.days_remaining;
            // Recalculate freshness percentage
            updatedItem.freshness_percentage = Math.round(
              (updates.days_remaining / item.original_freshness_days) * 100
            );
          }
          return updatedItem;
        });
      });

      // Close dialog immediately for better UX
      const previousEditingItem = editingItem;
      setEditingItem(null);

      return { previousItems, previousEditingItem };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
      toast({
        title: 'Item updated',
        description: 'The fridge item has been updated.',
      });
    },
    onError: (_error, _variables, context) => {
      // Rollback to previous state
      if (context?.previousItems) {
        queryClient.setQueryData(fridgeKeys.list(userId), context.previousItems);
      }
      // Restore editing state so user can retry
      if (context?.previousEditingItem) {
        setEditingItem(context.previousEditingItem);
      }
      toast({
        title: 'Failed to update item',
        description: 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const getFreshnessColor = (percentage: number) => {
    if (percentage > 60) return 'bg-green-500';
    if (percentage > 30) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getUrgencyBadge = (daysRemaining: number) => {
    if (daysRemaining <= 1) {
      return <Badge variant="destructive">Use today!</Badge>;
    }
    if (daysRemaining <= 2) {
      return <Badge className="bg-yellow-500">Use soon</Badge>;
    }
    return null;
  };

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (newItem.name && newItem.quantity) {
      addItemMutation.mutate({
        name: newItem.name,
        quantity: newItem.quantity,
        days: parseInt(newItem.days),
      });
    }
  };

  const handleSendExpiringAlert = async () => {
    setIsSendingEmail(true);
    try {
      await emailApi.sendExpiringAlert(2);
      toast({
        title: 'Email sent',
        description: 'Expiring items alert has been sent to your email.',
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

  const handleBulkImport = async (
    items: Array<{ ingredient_name: string; quantity: string; freshness_days: number }>
  ) => {
    // Cancel any outgoing refetches
    await queryClient.cancelQueries({ queryKey: fridgeKeys.all(userId) });

    // Snapshot the previous value
    const previousItems = queryClient.getQueryData<FridgeItem[]>(fridgeKeys.list(userId));

    // Optimistically add all items
    const optimisticItems: FridgeItem[] = items.map((item, index) => ({
      id: `temp-bulk-${Date.now()}-${index}`,
      ingredient_name: item.ingredient_name,
      quantity: item.quantity,
      days_remaining: item.freshness_days,
      original_freshness_days: item.freshness_days,
      added_date: new Date().toISOString(),
      freshness_percentage: 100,
    }));

    queryClient.setQueryData<FridgeItem[]>(fridgeKeys.list(userId), (old) => {
      return old ? [...old, ...optimisticItems] : optimisticItems;
    });

    setIsBulkImporting(true);
    try {
      await fridgeApi.addBulk(items);
      queryClient.invalidateQueries({ queryKey: fridgeKeys.all(userId) });
      toast({
        title: 'Items imported',
        description: `Successfully added ${items.length} item${items.length !== 1 ? 's' : ''} to your fridge.`,
      });
    } catch (error) {
      // Rollback to previous state
      queryClient.setQueryData(fridgeKeys.list(userId), previousItems);
      // Handle feature disabled error gracefully
      if (isFeatureDisabledError(error)) {
        toast({
          title: 'Feature unavailable',
          description: FEATURE_LABELS.fridge_bulk_import + ' is currently unavailable.',
        });
      } else {
        toast({
          title: 'Import failed',
          description: 'Could not import items. Please try again.',
          variant: 'destructive',
        });
      }
      throw new Error('Import failed'); // Re-throw so dialog knows import failed
    } finally {
      setIsBulkImporting(false);
    }
  };

  if (isLoading) {
    return <FridgeViewSkeleton />;
  }

  const sortedItems = [...(fridgeItems || [])].sort((a, b) => a.days_remaining - b.days_remaining);

  return (
    <div className="space-y-6" role="region" aria-label="Fridge Inventory">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold" id="fridge-heading">Fridge Inventory</h2>
          <p className="text-sm text-gray-600">Track your ingredients and their freshness</p>
        </div>
        {sortedItems.length > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setIsClearDialogOpen(true)}
            aria-label="Clear all items from fridge"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All
          </Button>
        )}
      </div>

      {expiringItems.length > 0 && (
        <Card className="border-destructive bg-destructive/5" role="alert" aria-live="polite">
          <CardContent className="py-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0" aria-hidden="true" />
                <div>
                  <p className="font-medium text-destructive">
                    {expiringItems.length} item{expiringItems.length > 1 ? 's' : ''} expiring soon!
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Use these ingredients first: {expiringItems.map((item) => item.ingredient_name).join(', ')}
                  </p>
                </div>
              </div>
              <div className="flex gap-2 ml-8 sm:ml-0 flex-shrink-0">
                <Link
                  href={`/recipes?ingredient=${encodeURIComponent(expiringItems[0].ingredient_name)}`}
                  aria-label={`Find recipes using ${expiringItems[0].ingredient_name}`}
                >
                  <Button variant="default" size="sm">
                    <ChefHat className="h-4 w-4 sm:mr-2" />
                    <span className="hidden sm:inline">Find Recipes</span>
                  </Button>
                </Link>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSendExpiringAlert}
                  disabled={isSendingEmail}
                  aria-label={isSendingEmail ? 'Sending email' : 'Email expiring items alert'}
                >
                  <Mail className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">{isSendingEmail ? 'Sending...' : 'Email Alert'}</span>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-lg">Add Ingredient</CardTitle>
          <FeatureGate
            feature="fridge_bulk_import"
            fallback={
              <DisabledFeatureButton
                feature="fridge_bulk_import"
                label="Bulk Import"
                icon={<Upload className="h-4 w-4 mr-2" />}
                size="sm"
              />
            }
          >
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsBulkImportOpen(true)}
              aria-label="Open bulk import dialog"
            >
              <Upload className="h-4 w-4 mr-2" />
              Bulk Import
            </Button>
          </FeatureGate>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAddItem} className="space-y-3 sm:space-y-0 sm:flex sm:gap-3 sm:items-end">
            <div className="flex-1">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={newItem.name}
                onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                placeholder="e.g., Chicken breast"
              />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:flex sm:gap-3">
              <div className="sm:w-28">
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  value={newItem.quantity}
                  onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
                  placeholder="e.g., 2 lbs"
                />
              </div>
              <div className="sm:w-20">
                <Label htmlFor="days">Days Fresh</Label>
                <Input
                  id="days"
                  type="number"
                  min="1"
                  value={newItem.days}
                  onChange={(e) => setNewItem({ ...newItem, days: e.target.value })}
                />
              </div>
            </div>
            <Button type="submit" disabled={addItemMutation.isPending} aria-label="Add ingredient to fridge" className="w-full sm:w-auto">
              Add
            </Button>
          </form>
        </CardContent>
      </Card>

      {sortedItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-500">Your fridge is empty. Add ingredients or generate a meal plan to stock up!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3" role="list" aria-label="Fridge items">
          {sortedItems.map((item) => {
            const descriptionId = `fridge-item-desc-${item.id}`;
            const freshnessLevel = item.freshness_percentage > 60 ? 'fresh' : item.freshness_percentage > 30 ? 'aging' : 'nearly expired';
            const urgencyText = item.days_remaining <= 1 ? 'Use today!' : item.days_remaining <= 2 ? 'Use soon.' : '';
            return (
              <Card key={item.id} role="listitem" aria-describedby={descriptionId}>
                <CardContent className="py-4">
                  {/* Visually hidden description for screen readers */}
                  <span id={descriptionId} className="sr-only">
                    {item.ingredient_name}: {item.quantity}, {item.days_remaining} days remaining,
                    {Math.round(item.freshness_percentage)}% freshness, currently {freshnessLevel}.
                    {urgencyText && ` ${urgencyText}`}
                  </span>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{item.ingredient_name}</span>
                        {getUrgencyBadge(item.days_remaining)}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {item.quantity} • {item.days_remaining} days remaining
                      </p>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={item.freshness_percentage}
                          className="h-2 flex-1"
                          indicatorClassName={getFreshnessColor(item.freshness_percentage)}
                          aria-label={`Freshness: ${Math.round(item.freshness_percentage)}%`}
                        />
                        <span className="text-xs text-gray-500 w-10" aria-hidden="true">{Math.round(item.freshness_percentage)}%</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        onClick={() => setEditingItem(item)}
                        aria-label={`Edit ${item.ingredient_name}`}
                        className="min-h-[44px] min-w-[44px] touch-manipulation"
                      >
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => removeItemMutation.mutate(item.id)}
                        className="min-h-[44px] px-4 text-red-600 hover:text-red-700 touch-manipulation"
                        aria-label={`Remove ${item.ingredient_name} from fridge`}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <BulkFridgeImportDialog
        open={isBulkImportOpen}
        onOpenChange={setIsBulkImportOpen}
        onImport={handleBulkImport}
        isLoading={isBulkImporting}
      />

      <ConfirmationDialog
        open={isClearDialogOpen}
        onOpenChange={setIsClearDialogOpen}
        title="Clear Fridge"
        description={`Are you sure you want to remove all ${sortedItems.length} item${sortedItems.length !== 1 ? 's' : ''} from your fridge? This action cannot be undone.`}
        confirmLabel="Clear All"
        onConfirm={() => clearFridgeMutation.mutate()}
        isLoading={clearFridgeMutation.isPending}
        variant="destructive"
      />

      <EditFridgeItemDialog
        open={editingItem !== null}
        onOpenChange={(open) => {
          if (!open) setEditingItem(null);
        }}
        item={editingItem}
        onSave={(id, updates) => updateItemMutation.mutate({ id, updates })}
        isLoading={updateItemMutation.isPending}
      />
    </div>
  );
}
