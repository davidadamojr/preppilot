'use client';

/**
 * SkipLink component for keyboard accessibility.
 *
 * Provides a visually hidden link that becomes visible on focus,
 * allowing keyboard users to skip navigation and jump directly
 * to the main content area.
 *
 * Usage:
 * 1. Place this component at the top of the page layout
 * 2. Ensure the main content area has id="main-content"
 *
 * @see https://www.w3.org/WAI/WCAG21/Techniques/general/G1
 */
export function SkipLink() {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      // Set tabindex to allow focus on non-focusable elements
      mainContent.setAttribute('tabindex', '-1');
      mainContent.focus();
      // Remove tabindex after blur to avoid keyboard trap
      mainContent.addEventListener('blur', () => {
        mainContent.removeAttribute('tabindex');
      }, { once: true });
    }
  };

  return (
    <a
      href="#main-content"
      onClick={handleClick}
      className="skip-link"
    >
      Skip to main content
    </a>
  );
}
