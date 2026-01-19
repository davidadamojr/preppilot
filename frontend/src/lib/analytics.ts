declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

export const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

export function pageview(url: string) {
  if (typeof window !== 'undefined' && window.gtag && GA_MEASUREMENT_ID) {
    window.gtag('config', GA_MEASUREMENT_ID, {
      page_path: url,
    });
  }
}

export function trackEvent(
  action: string,
  params?: Record<string, string | number | boolean>
) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, params);
  }
}

export const LandingEvents = {
  joinWaitlistClick: () => trackEvent('cta_click', { button: 'join_waitlist_nav' }),
  emailSubmit: () => trackEvent('email_submit', { location: 'hero' }),
  emailSubmitSuccess: () => trackEvent('email_submit_success', { location: 'hero' }),
  emailSubmitError: (error: string) =>
    trackEvent('email_submit_error', { location: 'hero', error }),
} as const;
