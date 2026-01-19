import { render, screen } from '@testing-library/react';
import { FeatureGate, DisabledFeatureButton, FEATURE_LABELS } from '../feature-gate';
import { useFeatureFlags } from '@/hooks/use-feature-flags';
import { Download } from 'lucide-react';

// Mock the useFeatureFlags hook
jest.mock('@/hooks/use-feature-flags', () => ({
  useFeatureFlags: jest.fn(),
}));

const mockedUseFeatureFlags = useFeatureFlags as jest.Mock;

describe('FeatureGate', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render children when feature is enabled', () => {
    mockedUseFeatureFlags.mockReturnValue({
      isEnabled: (feature: string) => feature === 'plan_duplication',
    });

    render(
      <FeatureGate feature="plan_duplication">
        <button>Duplicate</button>
      </FeatureGate>
    );

    expect(screen.getByRole('button', { name: 'Duplicate' })).toBeInTheDocument();
  });

  it('should not render children when feature is disabled', () => {
    mockedUseFeatureFlags.mockReturnValue({
      isEnabled: () => false,
    });

    render(
      <FeatureGate feature="plan_duplication">
        <button>Duplicate</button>
      </FeatureGate>
    );

    expect(screen.queryByRole('button', { name: 'Duplicate' })).not.toBeInTheDocument();
  });

  it('should render fallback when feature is disabled', () => {
    mockedUseFeatureFlags.mockReturnValue({
      isEnabled: () => false,
    });

    render(
      <FeatureGate
        feature="plan_duplication"
        fallback={<span>Feature unavailable</span>}
      >
        <button>Duplicate</button>
      </FeatureGate>
    );

    expect(screen.queryByRole('button', { name: 'Duplicate' })).not.toBeInTheDocument();
    expect(screen.getByText('Feature unavailable')).toBeInTheDocument();
  });

  it('should render nothing by default when feature is disabled and no fallback provided', () => {
    mockedUseFeatureFlags.mockReturnValue({
      isEnabled: () => false,
    });

    const { container } = render(
      <FeatureGate feature="plan_duplication">
        <button>Duplicate</button>
      </FeatureGate>
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe('DisabledFeatureButton', () => {
  it('should render a disabled button', () => {
    render(
      <DisabledFeatureButton
        feature="plan_duplication"
        label="Duplicate"
      />
    );

    const button = screen.getByRole('button', { name: /Duplicate - feature currently unavailable/i });
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it('should show tooltip with feature label', () => {
    render(
      <DisabledFeatureButton
        feature="plan_duplication"
        label="Duplicate"
      />
    );

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title', 'Plan duplication is currently unavailable');
  });

  it('should render with icon', () => {
    render(
      <DisabledFeatureButton
        feature="export_pdf"
        label="Export"
        icon={<Download data-testid="download-icon" className="h-4 w-4" />}
      />
    );

    expect(screen.getByTestId('download-icon')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('should apply size and variant props', () => {
    render(
      <DisabledFeatureButton
        feature="plan_duplication"
        label="Duplicate"
        size="sm"
        variant="destructive"
      />
    );

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('should hide label on mobile when showLabelOnMobile is false', () => {
    render(
      <DisabledFeatureButton
        feature="plan_duplication"
        label="Duplicate"
        showLabelOnMobile={false}
      />
    );

    // The label should be in a span with hidden sm:inline classes
    const span = screen.getByText('Duplicate');
    expect(span).toHaveClass('hidden', 'sm:inline');
  });
});

describe('FEATURE_LABELS', () => {
  it('should have labels for all 16 features', () => {
    const expectedFeatures = [
      'email_plan_notifications',
      'email_expiring_alerts',
      'email_adaptation_summaries',
      'export_pdf',
      'export_shopping_list',
      'plan_duplication',
      'plan_adaptation',
      'meal_swap',
      'fridge_bulk_import',
      'fridge_expiring_notifications',
      'recipe_search',
      'recipe_browser',
      'admin_user_management',
      'admin_audit_logs',
      'prep_timeline_optimization',
      'offline_mode',
    ];

    expectedFeatures.forEach((feature) => {
      expect(FEATURE_LABELS[feature as keyof typeof FEATURE_LABELS]).toBeDefined();
      expect(typeof FEATURE_LABELS[feature as keyof typeof FEATURE_LABELS]).toBe('string');
    });
  });

  it('should have human-readable labels', () => {
    expect(FEATURE_LABELS.plan_duplication).toBe('Plan duplication');
    expect(FEATURE_LABELS.meal_swap).toBe('Meal swapping');
    expect(FEATURE_LABELS.export_pdf).toBe('PDF export');
    expect(FEATURE_LABELS.fridge_bulk_import).toBe('Bulk import');
    expect(FEATURE_LABELS.plan_adaptation).toBe('Plan adaptation');
  });
});
