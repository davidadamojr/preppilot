import { Navbar } from './navbar';
import { HeroSection } from './hero-section';
import { ProblemSection } from './problem-section';
import { SolutionSection } from './solution-section';
import { HowItWorksSection } from './how-it-works-section';
import { LandingFooter } from './landing-footer';
import { LandingPageJsonLd } from '@/components/seo/json-ld';

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <LandingPageJsonLd />
      <Navbar />
      <main>
        <HeroSection />
        <ProblemSection />
        <SolutionSection />
        <HowItWorksSection />
      </main>
      <LandingFooter />
    </div>
  );
}
