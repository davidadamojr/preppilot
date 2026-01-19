'use client';

import { useState, useCallback } from 'react';
import { LandingEvents } from '@/lib/analytics';

type SubmitState = 'idle' | 'loading' | 'success' | 'error';

export function useEmailSubmit() {
  const [state, setState] = useState<SubmitState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const submit = useCallback(async (email: string) => {
    setState('loading');
    setErrorMessage(null);
    LandingEvents.emailSubmit();

    const startTime = Date.now();

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const elapsed = Date.now() - startTime;
      if (elapsed < 1500) {
        await new Promise((r) => setTimeout(r, 1500 - elapsed));
      }

      if (response.ok) {
        setState('success');
        LandingEvents.emailSubmitSuccess();
      } else {
        const data = await response.json();
        setState('error');
        setErrorMessage(data.error || 'Something went wrong');
        LandingEvents.emailSubmitError(data.error || 'unknown');
      }
    } catch {
      setState('error');
      setErrorMessage('Network error. Please try again.');
      LandingEvents.emailSubmitError('network');
    }
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setErrorMessage(null);
  }, []);

  return { state, errorMessage, submit, reset };
}
