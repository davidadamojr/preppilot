'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, Upload } from 'lucide-react';

export interface ParsedItem {
  ingredient_name: string;
  quantity: string;
  freshness_days: number;
  isValid: boolean;
  error?: string;
  lineNumber: number;
}

interface BulkFridgeImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (items: Array<{ ingredient_name: string; quantity: string; freshness_days: number }>) => Promise<void>;
  isLoading?: boolean;
}

/**
 * Parses a single line of bulk import text.
 * Expected format: "name, quantity, days" or "name, quantity" (defaults to 7 days)
 */
function parseLine(line: string, lineNumber: number): ParsedItem | null {
  const trimmed = line.trim();

  // Skip empty lines
  if (!trimmed) {
    return null;
  }

  // Skip comment lines
  if (trimmed.startsWith('#') || trimmed.startsWith('//')) {
    return null;
  }

  const parts = trimmed.split(',').map((p) => p.trim());

  if (parts.length < 2) {
    return {
      ingredient_name: parts[0] || '',
      quantity: '',
      freshness_days: 7,
      isValid: false,
      error: 'Missing quantity (format: name, quantity, days)',
      lineNumber,
    };
  }

  const name = parts[0];
  const quantity = parts[1];
  let freshnessDays = 7; // Default

  if (parts.length >= 3) {
    const parsed = parseInt(parts[2], 10);
    if (isNaN(parsed) || parsed < 1 || parsed > 365) {
      return {
        ingredient_name: name,
        quantity,
        freshness_days: 7,
        isValid: false,
        error: 'Days must be a number between 1 and 365',
        lineNumber,
      };
    }
    freshnessDays = parsed;
  }

  if (!name) {
    return {
      ingredient_name: '',
      quantity,
      freshness_days: freshnessDays,
      isValid: false,
      error: 'Ingredient name is required',
      lineNumber,
    };
  }

  if (!quantity) {
    return {
      ingredient_name: name,
      quantity: '',
      freshness_days: freshnessDays,
      isValid: false,
      error: 'Quantity is required',
      lineNumber,
    };
  }

  return {
    ingredient_name: name,
    quantity,
    freshness_days: freshnessDays,
    isValid: true,
    lineNumber,
  };
}

export function BulkFridgeImportDialog({
  open,
  onOpenChange,
  onImport,
  isLoading = false,
}: BulkFridgeImportDialogProps) {
  const [inputText, setInputText] = useState('');

  const parsedItems = useMemo(() => {
    const lines = inputText.split('\n');
    const items: ParsedItem[] = [];

    lines.forEach((line, index) => {
      const parsed = parseLine(line, index + 1);
      if (parsed) {
        items.push(parsed);
      }
    });

    return items;
  }, [inputText]);

  const validItems = parsedItems.filter((item) => item.isValid);
  const invalidItems = parsedItems.filter((item) => !item.isValid);

  const handleImport = useCallback(async () => {
    if (validItems.length === 0) return;

    const itemsToImport = validItems.map(({ ingredient_name, quantity, freshness_days }) => ({
      ingredient_name,
      quantity,
      freshness_days,
    }));

    await onImport(itemsToImport);
    setInputText('');
    onOpenChange(false);
  }, [validItems, onImport, onOpenChange]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setInputText('');
      onOpenChange(false);
    }
  }, [isLoading, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Bulk Import Ingredients
          </DialogTitle>
          <DialogDescription>
            Add multiple ingredients at once. Enter one item per line in the format:{' '}
            <code className="text-xs bg-muted px-1 py-0.5 rounded">name, quantity, days</code>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="bulk-input">Ingredients</Label>
            <textarea
              id="bulk-input"
              className="mt-1.5 w-full h-40 px-3 py-2 border rounded-md text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              placeholder={`chicken breast, 2 lbs, 5
carrots, 1 bunch, 7
milk, 1 gallon, 4
eggs, 12, 14`}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
              aria-describedby="bulk-input-help"
            />
            <p id="bulk-input-help" className="text-xs text-muted-foreground mt-1">
              Days is optional (defaults to 7). Lines starting with # are ignored.
            </p>
          </div>

          {parsedItems.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-4 text-sm">
                {validItems.length > 0 && (
                  <div className="flex items-center gap-1 text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{validItems.length} valid</span>
                  </div>
                )}
                {invalidItems.length > 0 && (
                  <div className="flex items-center gap-1 text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    <span>{invalidItems.length} invalid</span>
                  </div>
                )}
              </div>

              {/* Preview of valid items */}
              {validItems.length > 0 && (
                <div className="border rounded-md p-3 bg-muted/30 max-h-32 overflow-y-auto">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Preview:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {validItems.slice(0, 10).map((item, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {item.ingredient_name} ({item.quantity}, {item.freshness_days}d)
                      </Badge>
                    ))}
                    {validItems.length > 10 && (
                      <Badge variant="outline" className="text-xs">
                        +{validItems.length - 10} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {/* Show errors */}
              {invalidItems.length > 0 && (
                <div className="border border-destructive/30 rounded-md p-3 bg-destructive/5 max-h-24 overflow-y-auto">
                  <p className="text-xs font-medium text-destructive mb-1">Errors:</p>
                  <ul className="text-xs text-muted-foreground space-y-0.5">
                    {invalidItems.slice(0, 5).map((item, idx) => (
                      <li key={idx}>
                        Line {item.lineNumber}: {item.error}
                      </li>
                    ))}
                    {invalidItems.length > 5 && (
                      <li>...and {invalidItems.length - 5} more errors</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={validItems.length === 0 || isLoading}
            aria-label={isLoading ? 'Importing ingredients' : `Import ${validItems.length} ingredients`}
          >
            {isLoading ? 'Importing...' : `Import ${validItems.length} Item${validItems.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
