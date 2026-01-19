import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Display labels for user diet types.
 * Used in settings, dashboard, and profile editing.
 */
export const DIET_TYPE_LABELS: Record<string, string> = {
  low_histamine: 'Low Histamine',
  low_histamine_low_oxalate: 'Low Histamine + Low Oxalate',
  fodmap: 'Low FODMAP',
  fructose_free: 'Fructose Free',
};

/**
 * Options for diet type selection dropdowns.
 */
export const DIET_TYPE_OPTIONS = [
  { value: 'low_histamine', label: 'Low Histamine' },
  { value: 'low_histamine_low_oxalate', label: 'Low Histamine + Low Oxalate' },
  { value: 'fodmap', label: 'Low FODMAP' },
  { value: 'fructose_free', label: 'Fructose Free' },
];

/**
 * Format a diet tag for display (e.g., "low_histamine" -> "Low Histamine").
 * Falls back to title-casing if no explicit label exists.
 */
export function formatDietTag(tag: string): string {
  if (DIET_TYPE_LABELS[tag]) {
    return DIET_TYPE_LABELS[tag];
  }
  return tag
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
