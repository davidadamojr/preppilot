'use client';

import { ReactNode } from 'react';
import { useFeatureFlags } from '@/hooks/use-feature-flags';
import type { FeatureName } from '@/types';
import { Button } from '@/components/ui/button';

/**
 * Human-readable labels for feature flags.
 */
export const FEATURE_LABELS: Record<FeatureName, string> = {
  email_plan_notifications: 'Email notifications',
  email_expiring_alerts: 'Expiring item alerts',
  email_adaptation_summaries: 'Adaptation summaries',
  export_pdf: 'PDF export',
  export_shopping_list: 'Shopping list export',
  plan_duplication: 'Plan duplication',
  plan_adaptation: 'Plan adaptation',
  meal_swap: 'Meal swapping',
  fridge_bulk_import: 'Bulk import',
  fridge_expiring_notifications: 'Expiring notifications',
  recipe_search: 'Recipe search',
  recipe_browser: 'Recipe browser',
  admin_user_management: 'User management',
  admin_audit_logs: 'Audit logs',
  prep_timeline_optimization: 'Prep timeline optimization',
  llm_step_parsing: 'LLM step parsing',
  offline_mode: 'Offline mode',
};

interface FeatureGateProps {
  /** The feature flag to check */
  feature: FeatureName;
  /** Content to render when feature is enabled */
  children: ReactNode;
  /** Content to render when feature is disabled (optional - defaults to nothing) */
  fallback?: ReactNode;
}

/**
 * Conditionally render content based on feature flag status.
 *
 * Usage:
 * ```tsx
 * <FeatureGate feature="plan_duplication">
 *   <DuplicateButton />
 * </FeatureGate>
 *
 * // With fallback
 * <FeatureGate
 *   feature="plan_duplication"
 *   fallback={<span>Feature unavailable</span>}
 * >
 *   <DuplicateButton />
 * </FeatureGate>
 * ```
 */
export function FeatureGate({
  feature,
  children,
  fallback = null,
}: FeatureGateProps) {
  const { isEnabled } = useFeatureFlags();

  if (isEnabled(feature)) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
}

interface DisabledFeatureButtonProps {
  /** The feature that is disabled */
  feature: FeatureName;
  /** Label for the button */
  label: string;
  /** Icon to show (optional) */
  icon?: ReactNode;
  /** Button variant */
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  /** Button size */
  size?: 'default' | 'sm' | 'lg' | 'icon';
  /** Additional class names */
  className?: string;
  /** Show label on small screens (defaults to true) */
  showLabelOnMobile?: boolean;
}

/**
 * A disabled button with title tooltip explaining the feature is unavailable.
 *
 * Usage:
 * ```tsx
 * <FeatureGate
 *   feature="plan_duplication"
 *   fallback={
 *     <DisabledFeatureButton
 *       feature="plan_duplication"
 *       label="Duplicate"
 *       icon={<Copy className="h-4 w-4" />}
 *     />
 *   }
 * >
 *   <DuplicateButton />
 * </FeatureGate>
 * ```
 */
export function DisabledFeatureButton({
  feature,
  label,
  icon,
  variant = 'outline',
  size = 'default',
  className,
  showLabelOnMobile = true,
}: DisabledFeatureButtonProps) {
  const featureLabel = FEATURE_LABELS[feature] || feature.replace(/_/g, ' ');
  const tooltipText = `${featureLabel} is currently unavailable`;

  return (
    <Button
      variant={variant}
      size={size}
      disabled
      className={className}
      aria-label={`${label} - feature currently unavailable`}
      title={tooltipText}
    >
      {icon}
      {showLabelOnMobile ? (
        label
      ) : (
        <span className="hidden sm:inline">{label}</span>
      )}
    </Button>
  );
}
