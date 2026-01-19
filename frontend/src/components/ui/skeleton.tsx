import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton component with pulse animation.
 * Use this as a building block for content-aware loading states.
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-gray-200',
        className
      )}
      role="status"
      aria-label="Loading"
    />
  );
}

/**
 * Skeleton line for text content.
 */
export function SkeletonText({ className, lines = 1 }: SkeletonProps & { lines?: number }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton badge for status/tag indicators.
 */
export function SkeletonBadge({ className }: SkeletonProps) {
  return <Skeleton className={cn('h-5 w-16 rounded-full', className)} />;
}

/**
 * Skeleton button placeholder.
 */
export function SkeletonButton({ className, size = 'default' }: SkeletonProps & { size?: 'sm' | 'default' | 'lg' }) {
  const sizeClasses = {
    sm: 'h-8 w-16',
    default: 'h-10 w-24',
    lg: 'h-11 w-32',
  };
  return <Skeleton className={cn(sizeClasses[size], 'rounded-md', className)} />;
}

/**
 * Skeleton progress bar.
 */
export function SkeletonProgress({ className }: SkeletonProps) {
  return <Skeleton className={cn('h-2 w-full rounded-full', className)} />;
}

/**
 * Skeleton input field.
 */
export function SkeletonInput({ className }: SkeletonProps) {
  return <Skeleton className={cn('h-10 w-full rounded-md', className)} />;
}

/**
 * Skeleton card container - wrapper with proper spacing.
 */
export function SkeletonCard({ className, children }: SkeletonProps & { children?: React.ReactNode }) {
  return (
    <div
      className={cn(
        'rounded-xl border bg-card text-card-foreground shadow p-6',
        className
      )}
    >
      {children}
    </div>
  );
}
