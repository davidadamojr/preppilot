'use client';

import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { EmailCaptureForm } from './email-capture-form';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function HeroSection() {
  return (
    <section
      id="hero"
      className="min-h-screen flex items-center justify-center pt-16 pb-20 bg-gradient-to-b from-sage-50/50 to-white"
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6 }}
          >
            <Badge
              variant="secondary"
              className="mb-6 bg-sage-100 text-sage-800 hover:bg-sage-100 px-4 py-1.5 text-sm"
            >
              Finally: A Meal Planner for Histamine Intolerance
            </Badge>
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6"
          >
            Cook Fresh. Stay Safe.
          </motion.h1>

          <motion.p
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg sm:text-xl text-gray-600 mb-8 leading-relaxed"
          >
            The first meal planner that tracks{' '}
            <span className="font-semibold text-sage-700">ingredient age</span>{' '}
            in real-time. We prioritize your recipes based on what&apos;s in
            your fridge, so you use food before histamine levels rise.
          </motion.p>

          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="max-w-md mx-auto mb-6"
          >
            <EmailCaptureForm />
          </motion.div>

          <motion.p
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-sm text-gray-500"
          >
            Smart inventory tracking for Low-Histamine & MAST diets.
          </motion.p>
        </div>
      </div>
    </section>
  );
}
