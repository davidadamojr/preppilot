import { LandingPage } from '@/components/landing/landing-page';
import { LiveModeRedirect } from '@/components/live-mode-redirect';

const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE || 'live';

export default function Home() {
  if (APP_MODE === 'pretotype') {
    return <LandingPage />;
  }
  return <LiveModeRedirect />;
}
