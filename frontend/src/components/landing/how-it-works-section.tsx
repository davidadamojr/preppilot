'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface PantryItem {
  name: string;
  timeLeft: string;
  urgency: 'high' | 'medium' | 'low';
}

const pantryItems: PantryItem[] = [
  { name: 'Fresh Salmon', timeLeft: 'Use within 12 hours', urgency: 'high' },
  { name: 'Ground Beef', timeLeft: 'Use within 24 hours', urgency: 'high' },
  { name: 'Chicken Breast', timeLeft: 'Safe for 2 days', urgency: 'medium' },
  { name: 'Zucchini', timeLeft: 'Safe for 3 days', urgency: 'low' },
  { name: 'Bell Peppers', timeLeft: 'Safe for 5 days', urgency: 'low' },
];

const urgencyStyles = {
  high: {
    badge: 'bg-alert-100 text-alert-700 border-alert-200',
    indicator: 'bg-alert-500',
  },
  medium: {
    badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    indicator: 'bg-yellow-500',
  },
  low: {
    badge: 'bg-sage-100 text-sage-700 border-sage-200',
    indicator: 'bg-sage-500',
  },
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.4 } },
};

export function HowItWorksSection() {
  return (
    <section className="py-20 bg-white">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Your Digital Pantry
          </h2>
          <p className="text-lg text-gray-600">
            Prioritize your cooking based on safety.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="max-w-lg mx-auto"
        >
          <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden shadow-lg">
            <div className="bg-sage-600 px-4 py-3">
              <h3 className="text-white font-medium">My Fridge</h3>
            </div>
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              className="divide-y divide-gray-100"
            >
              {pantryItems.map((item) => (
                <motion.div
                  key={item.name}
                  variants={itemVariants}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-100/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'w-2 h-2 rounded-full',
                        urgencyStyles[item.urgency].indicator
                      )}
                    />
                    <span className="font-medium text-gray-900">
                      {item.name}
                    </span>
                  </div>
                  <span
                    className={cn(
                      'text-xs px-2.5 py-1 rounded-full border',
                      urgencyStyles[item.urgency].badge
                    )}
                  >
                    {item.timeLeft}
                  </span>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
