'use client';

import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { ShoppingBag, AlertTriangle, CalendarClock } from 'lucide-react';

const problems = [
  {
    icon: ShoppingBag,
    title: 'Ingredients Age Quickly.',
    description:
      'High-protein foods like fish and meat build histamine the longer they sit raw.',
  },
  {
    icon: AlertTriangle,
    title: 'Waste & Fear.',
    description:
      "Throwing out food because you 'aren't sure' if it's safe anymore is expensive and stressful.",
  },
  {
    icon: CalendarClock,
    title: 'Poor Planning.',
    description:
      'Buying fresh food but cooking it 3 days later is a recipe for a flare-up.',
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function ProblemSection() {
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
            The Invisible Timer in Your Fridge.
          </h2>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {problems.map((problem) => (
            <motion.div key={problem.title} variants={itemVariants}>
              <Card className="h-full border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="w-12 h-12 rounded-lg bg-alert-50 flex items-center justify-center mb-4">
                    <problem.icon className="h-6 w-6 text-alert-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {problem.title}
                  </h3>
                  <p className="text-gray-600">{problem.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
