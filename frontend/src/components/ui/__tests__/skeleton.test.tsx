import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Skeleton,
  SkeletonText,
  SkeletonBadge,
  SkeletonButton,
  SkeletonProgress,
  SkeletonInput,
  SkeletonCard,
} from '../skeleton';

describe('Skeleton', () => {
  it('should render with base styles', () => {
    const { container } = render(<Skeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-gray-200');
  });

  it('should have role="status" for accessibility', () => {
    render(<Skeleton />);

    const skeleton = screen.getByRole('status');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute('aria-label', 'Loading');
  });

  it('should accept custom className', () => {
    const { container } = render(<Skeleton className="h-10 w-20" />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('h-10', 'w-20');
  });
});

describe('SkeletonText', () => {
  it('should render single line by default', () => {
    const { container } = render(<SkeletonText />);

    const lines = container.querySelectorAll('[role="status"]');
    expect(lines).toHaveLength(1);
  });

  it('should render multiple lines when specified', () => {
    const { container } = render(<SkeletonText lines={3} />);

    const lines = container.querySelectorAll('[role="status"]');
    expect(lines).toHaveLength(3);
  });

  it('should make last line shorter when multiple lines', () => {
    const { container } = render(<SkeletonText lines={2} />);

    const lines = container.querySelectorAll('[role="status"]');
    expect(lines[1]).toHaveClass('w-3/4');
    expect(lines[0]).toHaveClass('w-full');
  });
});

describe('SkeletonBadge', () => {
  it('should render with badge-like dimensions', () => {
    const { container } = render(<SkeletonBadge />);

    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('h-5', 'w-16', 'rounded-full');
  });

  it('should accept custom className', () => {
    const { container } = render(<SkeletonBadge className="w-24" />);

    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('w-24');
  });
});

describe('SkeletonButton', () => {
  it('should render with default size', () => {
    const { container } = render(<SkeletonButton />);

    const button = container.firstChild as HTMLElement;
    expect(button).toHaveClass('h-10', 'w-24', 'rounded-md');
  });

  it('should render with small size', () => {
    const { container } = render(<SkeletonButton size="sm" />);

    const button = container.firstChild as HTMLElement;
    expect(button).toHaveClass('h-8', 'w-16');
  });

  it('should render with large size', () => {
    const { container } = render(<SkeletonButton size="lg" />);

    const button = container.firstChild as HTMLElement;
    expect(button).toHaveClass('h-11', 'w-32');
  });
});

describe('SkeletonProgress', () => {
  it('should render with progress bar dimensions', () => {
    const { container } = render(<SkeletonProgress />);

    const progress = container.firstChild as HTMLElement;
    expect(progress).toHaveClass('h-2', 'w-full', 'rounded-full');
  });
});

describe('SkeletonInput', () => {
  it('should render with input-like dimensions', () => {
    const { container } = render(<SkeletonInput />);

    const input = container.firstChild as HTMLElement;
    expect(input).toHaveClass('h-10', 'w-full', 'rounded-md');
  });
});

describe('SkeletonCard', () => {
  it('should render with card styles', () => {
    const { container } = render(<SkeletonCard />);

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('rounded-xl', 'border', 'bg-card', 'shadow', 'p-6');
  });

  it('should render children', () => {
    render(
      <SkeletonCard>
        <span data-testid="child">Child content</span>
      </SkeletonCard>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});
