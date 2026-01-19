'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { LandingEvents } from '@/lib/analytics';
import { cn } from '@/lib/utils';

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToHero = () => {
    LandingEvents.joinWaitlistClick();
    const heroSection = document.getElementById('hero');
    if (heroSection) {
      heroSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        isScrolled
          ? 'bg-white/95 backdrop-blur-sm shadow-sm'
          : 'bg-transparent'
      )}
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-sage-700">PrepPilot</span>
          </div>
          <Button
            onClick={scrollToHero}
            className="bg-sage-600 hover:bg-sage-700 text-white"
          >
            Join Waitlist
          </Button>
        </div>
      </div>
    </nav>
  );
}
