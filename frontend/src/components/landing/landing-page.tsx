import { Navbar } from './navbar';
import { HeroSection } from './hero-section';
import { ProblemSection } from './problem-section';
import { SolutionSection } from './solution-section';
import { HowItWorksSection } from './how-it-works-section';
import { LandingFooter } from './landing-footer';

export function LandingPage() {
  return (
    <div className="min-h-screen">
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
