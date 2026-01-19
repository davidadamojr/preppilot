'use client';

import { useState, FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEmailSubmit } from '@/hooks/use-email-submit';
import { Loader2, CheckCircle2 } from 'lucide-react';

export function EmailCaptureForm() {
  const [email, setEmail] = useState('');
  const { state, errorMessage, submit } = useEmailSubmit();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      submit(email.trim());
    }
  };

  if (state === 'success') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-3 p-4 bg-sage-50 rounded-lg border border-sage-200"
      >
        <CheckCircle2 className="h-6 w-6 text-sage-600 flex-shrink-0" />
        <p className="text-sage-800 font-medium">
          You&apos;re on the list! We&apos;ll notify you when we&apos;re ready for you to use PrepPilot.
        </p>
      </motion.div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          type="email"
          placeholder="Enter your email address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={state === 'loading'}
          className="flex-1 h-12 text-base"
          required
        />
        <Button
          type="submit"
          disabled={state === 'loading' || !email.trim()}
          className="h-12 px-6 bg-sage-600 hover:bg-sage-700 text-white font-medium whitespace-nowrap"
        >
          <AnimatePresence mode="wait">
            {state === 'loading' ? (
              <motion.span
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Joining...</span>
              </motion.span>
            ) : (
              <motion.span
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                Join Waitlist
              </motion.span>
            )}
          </AnimatePresence>
        </Button>
      </div>
      {state === 'error' && errorMessage && (
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 text-sm text-red-600"
        >
          {errorMessage}
        </motion.p>
      )}
    </form>
  );
}