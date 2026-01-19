import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import {
  PlanViewSkeleton,
  FridgeViewSkeleton,
  CatchUpViewSkeleton,
  SettingsViewSkeleton,
  RecipeGridSkeleton,
  RecipeBrowserSkeleton,
  DashboardSkeleton,
  ExclusionsListSkeleton,
} from '../skeletons';

describe('PlanViewSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<PlanViewSkeleton />);

    // The outer container has the main status role with aria-label
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading meal plans');
  });

  it('should render 3 day card skeletons', () => {
    const { container } = render(<PlanViewSkeleton />);

    // Each day card has 3 meal rows
    const mealRows = container.querySelectorAll('.bg-gray-50.rounded-lg');
    expect(mealRows.length).toBe(9); // 3 days * 3 meals
  });
});

describe('FridgeViewSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<FridgeViewSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading fridge inventory');
  });

  it('should render fridge item skeletons', () => {
    const { container } = render(<FridgeViewSkeleton />);

    // Should have 5 fridge item cards
    const cards = container.querySelectorAll('.grid.gap-3 > div');
    expect(cards.length).toBe(5);
  });
});

describe('CatchUpViewSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<CatchUpViewSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading catch-up suggestions');
  });

  it('should render section skeletons', () => {
    const { container } = render(<CatchUpViewSkeleton />);

    // Should have 3 section cards (missed preps, expiring, pending)
    const sectionCards = container.querySelectorAll('.space-y-4 > div');
    expect(sectionCards.length).toBe(3);
  });
});

describe('SettingsViewSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<SettingsViewSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading settings');
  });

  it('should render all settings cards', () => {
    const { container } = render(<SettingsViewSkeleton />);

    // Profile, Exclusions, Password, Danger Zone = 4 cards
    const cards = container.querySelectorAll('.rounded-xl.border');
    expect(cards.length).toBe(4);
  });
});

describe('ExclusionsListSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<ExclusionsListSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading dietary exclusions');
  });

  it('should render checkbox skeletons', () => {
    const { container } = render(<ExclusionsListSkeleton />);

    // Should have 6 checkbox rows
    const checkboxRows = container.querySelectorAll('.flex.items-center.space-x-2');
    expect(checkboxRows.length).toBe(6);
  });
});

describe('RecipeGridSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<RecipeGridSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading recipes');
  });

  it('should render recipe card skeletons in a grid', () => {
    const { container } = render(<RecipeGridSkeleton />);

    // Should have 6 recipe cards
    const grid = container.querySelector('.grid');
    expect(grid).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3');
    const cards = grid?.querySelectorAll('.rounded-xl');
    expect(cards?.length).toBe(6);
  });
});

describe('RecipeBrowserSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<RecipeBrowserSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading recipes');
  });

  it('should include search/filter skeleton and recipe grid', () => {
    const { container } = render(<RecipeBrowserSkeleton />);

    // Should have the filter card and recipe grid
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBeGreaterThan(6); // Filter card + 6 recipe cards
  });
});

describe('DashboardSkeleton', () => {
  it('should render with accessible loading state', () => {
    const { container } = render(<DashboardSkeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Loading dashboard');
  });

  it('should render header skeleton', () => {
    const { container } = render(<DashboardSkeleton />);

    const header = container.querySelector('header');
    expect(header).toBeInTheDocument();
    expect(header).toHaveClass('bg-white', 'border-b');
  });

  it('should render tabs skeleton', () => {
    const { container } = render(<DashboardSkeleton />);

    // Tab skeleton has a 4-column grid
    const tabsGrid = container.querySelector('.grid.grid-cols-4');
    expect(tabsGrid).toBeInTheDocument();
  });

  it('should include PlanViewSkeleton as default content', () => {
    const { container } = render(<DashboardSkeleton />);

    // Should have meal row skeletons from PlanViewSkeleton
    const mealRows = container.querySelectorAll('.bg-gray-50.rounded-lg');
    expect(mealRows.length).toBe(9); // 3 days * 3 meals
  });
});
