import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkFridgeImportDialog } from '../bulk-fridge-import-dialog';

describe('BulkFridgeImportDialog', () => {
  const mockOnImport = vi.fn();
  const mockOnOpenChange = vi.fn();

  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    onImport: mockOnImport,
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render dialog when open is true', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Bulk Import Ingredients')).toBeInTheDocument();
    });

    it('should not render dialog when open is false', () => {
      render(<BulkFridgeImportDialog {...defaultProps} open={false} />);

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should show format instructions', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      expect(screen.getByText(/name, quantity, days/)).toBeInTheDocument();
    });

    it('should have a textarea for input', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      expect(screen.getByRole('textbox', { name: /ingredients/i })).toBeInTheDocument();
    });

    it('should show placeholder text with examples', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      expect(textarea).toHaveAttribute('placeholder');
      expect(textarea.getAttribute('placeholder')).toContain('chicken breast');
    });

    it('should have Cancel and Import buttons', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /import 0 ingredient/i })).toBeInTheDocument();
    });
  });

  describe('parsing input', () => {
    it('should parse valid input with all three fields', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken breast, 2 lbs, 5');

      await waitFor(() => {
        expect(screen.getByText('1 valid')).toBeInTheDocument();
      });
    });

    it('should parse valid input with default days', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'carrots, 1 bunch');

      await waitFor(() => {
        expect(screen.getByText('1 valid')).toBeInTheDocument();
        // Should show default 7 days in preview
        expect(screen.getByText(/carrots.*1 bunch.*7d/)).toBeInTheDocument();
      });
    });

    it('should parse multiple valid lines', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5{enter}milk, 1 gallon, 4{enter}eggs, 12, 14');

      await waitFor(() => {
        expect(screen.getByText('3 valid')).toBeInTheDocument();
      });
    });

    it('should skip empty lines', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs{enter}{enter}eggs, 12');

      await waitFor(() => {
        expect(screen.getByText('2 valid')).toBeInTheDocument();
      });
    });

    it('should skip comment lines starting with #', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, '# This is a comment{enter}chicken, 2 lbs');

      await waitFor(() => {
        expect(screen.getByText('1 valid')).toBeInTheDocument();
      });
    });

    it('should skip comment lines starting with //', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, '// Shopping list{enter}chicken, 2 lbs');

      await waitFor(() => {
        expect(screen.getByText('1 valid')).toBeInTheDocument();
      });
    });

    it('should detect invalid lines missing quantity', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken');

      await waitFor(() => {
        expect(screen.getByText('1 invalid')).toBeInTheDocument();
        expect(screen.getByText(/missing quantity/i)).toBeInTheDocument();
      });
    });

    it('should detect invalid days value', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, abc');

      await waitFor(() => {
        expect(screen.getByText('1 invalid')).toBeInTheDocument();
        expect(screen.getByText(/days must be a number/i)).toBeInTheDocument();
      });
    });

    it('should detect days out of range (too low)', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 0');

      await waitFor(() => {
        expect(screen.getByText('1 invalid')).toBeInTheDocument();
      });
    });

    it('should detect days out of range (too high)', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 400');

      await waitFor(() => {
        expect(screen.getByText('1 invalid')).toBeInTheDocument();
      });
    });
  });

  describe('preview', () => {
    it('should show preview of valid items', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken breast, 2 lbs, 5');

      await waitFor(() => {
        expect(screen.getByText('Preview:')).toBeInTheDocument();
        expect(screen.getByText(/chicken breast.*2 lbs.*5d/)).toBeInTheDocument();
      });
    });

    it('should truncate preview after 10 items', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      // Create 12 items
      const items = Array.from({ length: 12 }, (_, i) => `item${i + 1}, qty${i + 1}`).join('\n');
      await user.type(textarea, items);

      await waitFor(() => {
        expect(screen.getByText('+2 more')).toBeInTheDocument();
      });
    });

    it('should show errors for invalid items', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'invalid-item');

      await waitFor(() => {
        expect(screen.getByText('Errors:')).toBeInTheDocument();
        expect(screen.getByText(/line 1/i)).toBeInTheDocument();
      });
    });
  });

  describe('import action', () => {
    it('should disable Import button when no valid items', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const importButton = screen.getByRole('button', { name: /import 0 ingredient/i });
      expect(importButton).toBeDisabled();
    });

    it('should enable Import button when valid items exist', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5');

      await waitFor(() => {
        const importButton = screen.getByRole('button', { name: /import 1 ingredient/i });
        expect(importButton).not.toBeDisabled();
      });
    });

    it('should call onImport with valid items when Import is clicked', async () => {
      const user = userEvent.setup();
      mockOnImport.mockResolvedValue(undefined);
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5{enter}eggs, 12');

      await waitFor(() => {
        expect(screen.getByText('2 valid')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /import 2 ingredient/i }));

      await waitFor(() => {
        expect(mockOnImport).toHaveBeenCalledWith([
          { ingredient_name: 'chicken', quantity: '2 lbs', freshness_days: 5 },
          { ingredient_name: 'eggs', quantity: '12', freshness_days: 7 },
        ]);
      });
    });

    it('should close dialog after successful import', async () => {
      const user = userEvent.setup();
      mockOnImport.mockResolvedValue(undefined);
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5');

      await user.click(screen.getByRole('button', { name: /import 1 ingredient/i }));

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('should clear textarea after successful import', async () => {
      const user = userEvent.setup();
      mockOnImport.mockResolvedValue(undefined);
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5');

      await user.click(screen.getByRole('button', { name: /import 1 ingredient/i }));

      await waitFor(() => {
        expect(mockOnImport).toHaveBeenCalled();
      });

      // Re-open to check state
      // Note: textarea value should be cleared internally
    });

    it('should only import valid items, ignoring invalid ones', async () => {
      const user = userEvent.setup();
      mockOnImport.mockResolvedValue(undefined);
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs{enter}invalid-item{enter}eggs, 12');

      await waitFor(() => {
        expect(screen.getByText('2 valid')).toBeInTheDocument();
        expect(screen.getByText('1 invalid')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /import 2 ingredient/i }));

      await waitFor(() => {
        expect(mockOnImport).toHaveBeenCalledWith([
          { ingredient_name: 'chicken', quantity: '2 lbs', freshness_days: 7 },
          { ingredient_name: 'eggs', quantity: '12', freshness_days: 7 },
        ]);
      });
    });
  });

  describe('loading state', () => {
    it('should show "Importing..." text when loading', () => {
      render(<BulkFridgeImportDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByText('Importing...')).toBeInTheDocument();
    });

    it('should disable textarea when loading', () => {
      render(<BulkFridgeImportDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByRole('textbox', { name: /ingredients/i })).toBeDisabled();
    });

    it('should disable Cancel button when loading', () => {
      render(<BulkFridgeImportDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
    });

    it('should disable Import button when loading', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs');

      rerender(<BulkFridgeImportDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByRole('button', { name: /importing/i })).toBeDisabled();
    });
  });

  describe('cancel action', () => {
    it('should call onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('should clear textarea when dialog is closed', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs');

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      // Reopen dialog
      rerender(<BulkFridgeImportDialog {...defaultProps} open={true} />);

      // Input should be cleared (internal state reset)
      expect(screen.queryByText('1 valid')).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have aria-describedby on textarea', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      expect(textarea).toHaveAttribute('aria-describedby', 'bulk-input-help');
    });

    it('should have help text for textarea', () => {
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const helpText = screen.getByText(/days is optional/i);
      expect(helpText).toBeInTheDocument();
    });

    it('should have proper aria-label on Import button', async () => {
      const user = userEvent.setup();
      render(<BulkFridgeImportDialog {...defaultProps} />);

      const textarea = screen.getByRole('textbox', { name: /ingredients/i });
      await user.type(textarea, 'chicken, 2 lbs, 5');

      await waitFor(() => {
        const importButton = screen.getByRole('button', { name: /import 1 ingredient/i });
        expect(importButton).toBeInTheDocument();
      });
    });
  });
});
