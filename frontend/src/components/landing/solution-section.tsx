'use client';

import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Timer, Utensils, FilterX } from 'lucide-react';

const features = [
  {
    icon: Timer,
    title: 'Smart Ingredient Tracking.',
    description:
      'Log your groceries, and PrepPilot monitors their age. It alerts you to cook high-risk items (meat/fish) first.',
  },
  {
    icon: Utensils,
    title: 'Freshness-Based Recipes.',
    description:
      "The algorithm suggests meals based on what needs to be used *today*, not a random schedule.",
  },
  {
    icon: FilterX,
    title: 'Strict Exclusion Filters.',
    description:
      'Filter for Low-Histamine, Gluten-Free, Dairy-Free, and 18+ other allergens simultaneously.',
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

export function SolutionSection() {
  return (
    <section className="py-20 bg-sage-50/50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Just-in-Time Meal Planning.
          </h2>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature) => (
            <motion.div key={feature.title} variants={itemVariants}>
              <Card className="h-full bg-white border-sage-100 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="w-12 h-12 rounded-lg bg-sage-100 flex items-center justify-center mb-4">
                    <feature.icon className="h-6 w-6 text-sage-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
