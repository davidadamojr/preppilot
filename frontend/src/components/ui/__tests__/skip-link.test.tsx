import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SkipLink } from '../skip-link';

describe('SkipLink', () => {
  let mainContent: HTMLElement;

  beforeEach(() => {
    // Create a mock main content element
    mainContent = document.createElement('main');
    mainContent.id = 'main-content';
    mainContent.textContent = 'Main content area';
    document.body.appendChild(mainContent);
  });

  afterEach(() => {
    // Clean up the mock element
    if (mainContent && mainContent.parentNode) {
      mainContent.parentNode.removeChild(mainContent);
    }
  });

  it('should render a skip link with correct text', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link).toBeInTheDocument();
  });

  it('should have href pointing to main-content', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link).toHaveAttribute('href', '#main-content');
  });

  it('should have skip-link class for styling', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link).toHaveClass('skip-link');
  });

  it('should focus main content when clicked', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });
    const focusSpy = vi.spyOn(mainContent, 'focus');

    fireEvent.click(link);

    expect(focusSpy).toHaveBeenCalled();
  });

  it('should set tabindex on main content when clicked', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });

    fireEvent.click(link);

    expect(mainContent).toHaveAttribute('tabindex', '-1');
  });

  it('should remove tabindex from main content on blur', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });

    fireEvent.click(link);
    expect(mainContent).toHaveAttribute('tabindex', '-1');

    fireEvent.blur(mainContent);
    expect(mainContent).not.toHaveAttribute('tabindex');
  });

  it('should prevent default link behavior', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });
    const clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
    const preventDefaultSpy = vi.spyOn(clickEvent, 'preventDefault');

    link.dispatchEvent(clickEvent);

    expect(preventDefaultSpy).toHaveBeenCalled();
  });

  it('should handle missing main-content element gracefully', () => {
    // Remove the main content element
    mainContent.parentNode?.removeChild(mainContent);

    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });

    // Should not throw an error
    expect(() => fireEvent.click(link)).not.toThrow();
  });

  it('should be focusable for keyboard navigation', () => {
    render(<SkipLink />);

    const link = screen.getByRole('link', { name: /skip to main content/i });

    link.focus();
    expect(document.activeElement).toBe(link);
  });
});
