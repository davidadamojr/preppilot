# PrepPilot Pretotype Landing Page - Implementation Plan

## Overview

Build a "Fake Door" pretotype landing page for PrepPilot to validate interest in a Low-Histamine Meal Planner by collecting waitlist emails. The system supports **environment-based mode switching** between pretotype (landing page) and live (authenticated app) modes.

---

## Mode Switching Architecture

### Environment Variable

```bash
# .env.local
NEXT_PUBLIC_APP_MODE=pretotype  # Options: "pretotype" | "live"
```

### Behavior by Mode

| Mode | Root URL (`/`) Behavior | Auth Required |
|------|------------------------|---------------|
| `pretotype` | Shows landing page with email capture | No |
| `live` | Redirects to `/dashboard` (auth) or `/login` | Yes |

### Implementation Strategy

Create a **mode-aware root page** that conditionally renders:
- **Pretotype mode**: Landing page component (server-rendered, no auth)
- **Live mode**: Current redirect logic (client-rendered, auth-aware)

```tsx
// src/app/page.tsx
import { LandingPage } from '@/components/landing/landing-page';
import { LiveModeRedirect } from '@/components/live-mode-redirect';

const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE || 'live';

export default function Home() {
  if (APP_MODE === 'pretotype') {
    return <LandingPage />;
  }
  return <LiveModeRedirect />;
}
```

---

## File Structure

### New Files

```
frontend/src/
├── app/
│   └── api/
│       └── waitlist/
│           └── route.ts               # Server-side API for form submission
├── components/
│   ├── landing/
│   │   ├── landing-page.tsx           # Main landing page container
│   │   ├── navbar.tsx                 # Fixed navigation bar
│   │   ├── hero-section.tsx           # Hero with email capture
│   │   ├── email-capture-form.tsx     # Form component (calls internal API)
│   │   ├── problem-section.tsx        # Pain point cards
│   │   ├── solution-section.tsx       # Feature cards
│   │   ├── how-it-works-section.tsx   # Digital pantry visualization
│   │   └── landing-footer.tsx         # Footer with disclaimer
│   └── live-mode-redirect.tsx         # Extracted current redirect logic
├── lib/
│   └── analytics.ts                   # Google Analytics utilities
└── hooks/
    └── use-email-submit.ts            # Form submission state hook

frontend/public/
├── images/
│   ├── logo.svg                       # PrepPilot logo
│   └── og-image.png                   # Open Graph image (1200x630)
├── favicon.ico                        # Sage green favicon
└── apple-touch-icon.png               # 180x180 touch icon
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/app/page.tsx` | Mode-switching logic |
| `src/app/layout.tsx` | Add GA script, update metadata |
| `src/app/globals.css` | Add sage/alert color variables |
| `tailwind.config.ts` | Add sage/alert color palette |
| `package.json` | Add `framer-motion` |
| `.env.local` | Add mode, Formspree, GA variables |

---

## Server-Side Form Submission (API Route)

### Why Server-Side Proxy?

1. **Security**: Hides Formspree form ID from client-side code
2. **Validation**: Server-side email validation before forwarding
3. **Rate Limiting**: Can add rate limiting at the API level
4. **Flexibility**: Easy to swap Formspree for another service later
5. **Logging**: Can log submissions server-side for debugging

### Environment Variables (Server-Side)

```bash
# .env.local (NOT prefixed with NEXT_PUBLIC_ - server-only)
FORMSPREE_FORM_ID=your_form_id
```

### API Route Implementation (app/api/waitlist/route.ts)

```typescript
import { NextRequest, NextResponse } from 'next/server';

const FORMSPREE_FORM_ID = process.env.FORMSPREE_FORM_ID;

// Simple email validation
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email } = body;

    // Validation
    if (!email || typeof email !== 'string') {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    if (!isValidEmail(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    if (!FORMSPREE_FORM_ID) {
      console.error('FORMSPREE_FORM_ID not configured');
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    // Forward to Formspree
    const formspreeResponse = await fetch(
      `https://formspree.io/f/${FORMSPREE_FORM_ID}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ email }),
      }
    );

    if (!formspreeResponse.ok) {
      const errorData = await formspreeResponse.json();
      console.error('Formspree error:', errorData);
      return NextResponse.json(
        { error: 'Failed to submit email' },
        { status: 502 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Waitlist submission error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

### Client-Side Form Hook (hooks/use-email-submit.ts)

```typescript
'use client';

import { useState, useCallback } from 'react';
import { trackEvent } from '@/lib/analytics';

type SubmitState = 'idle' | 'loading' | 'success' | 'error';

export function useEmailSubmit() {
  const [state, setState] = useState<SubmitState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const submit = useCallback(async (email: string) => {
    setState('loading');
    setErrorMessage(null);

    const startTime = Date.now();

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      // Ensure minimum 1.5s loading time for UX
      const elapsed = Date.now() - startTime;
      if (elapsed < 1500) {
        await new Promise((r) => setTimeout(r, 1500 - elapsed));
      }

      if (response.ok) {
        setState('success');
        trackEvent('email_submit_success', { location: 'hero' });
      } else {
        const data = await response.json();
        setState('error');
        setErrorMessage(data.error || 'Something went wrong');
        trackEvent('email_submit_error', { location: 'hero', error: data.error });
      }
    } catch {
      setState('error');
      setErrorMessage('Network error. Please try again.');
      trackEvent('email_submit_error', { location: 'hero', error: 'network' });
    }
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setErrorMessage(null);
  }, []);

  return { state, errorMessage, submit, reset };
}
```

---

## Color System

### CSS Variables (globals.css)

```css
:root {
  /* Sage Green - Primary brand color */
  --sage-50: 138 76% 97%;
  --sage-100: 141 84% 93%;
  --sage-200: 141 79% 85%;
  --sage-300: 142 77% 73%;
  --sage-400: 142 69% 58%;
  --sage-500: 142 71% 45%;
  --sage-600: 142 76% 36%;
  --sage-700: 142 72% 29%;
  --sage-800: 144 61% 20%;
  --sage-900: 145 63% 16%;

  /* Alert Orange - Accent/urgency */
  --alert-50: 33 100% 96%;
  --alert-100: 34 100% 91%;
  --alert-200: 32 98% 83%;
  --alert-300: 31 97% 72%;
  --alert-400: 27 96% 61%;
  --alert-500: 25 95% 53%;
  --alert-600: 21 90% 48%;
  --alert-700: 17 88% 40%;
  --alert-800: 15 79% 34%;
  --alert-900: 15 75% 28%;
}
```

### Tailwind Config Extension

```typescript
colors: {
  sage: {
    50: 'hsl(var(--sage-50))',
    100: 'hsl(var(--sage-100))',
    // ... 200-800
    900: 'hsl(var(--sage-900))',
  },
  alert: {
    50: 'hsl(var(--alert-50))',
    // ... 100-800
    900: 'hsl(var(--alert-900))',
  },
}
```

---

## Google Analytics Setup

### Environment Variable

```bash
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### Script Integration (layout.tsx)

```tsx
import Script from 'next/script';

const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

// In RootLayout, before </body>:
{GA_ID && (
  <>
    <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
    <Script id="ga-init" strategy="afterInteractive">
      {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}
        gtag('js',new Date());gtag('config','${GA_ID}');`}
    </Script>
  </>
)}
```

### CTA Events to Track

| Event | Trigger | Parameters |
|-------|---------|------------|
| `cta_click` | "Join Beta" nav button | `{ button: 'join_beta_nav' }` |
| `email_submit` | Form submit clicked | `{ location: 'hero' }` |
| `email_submit_success` | API returns success | `{ location: 'hero' }` |
| `email_submit_error` | API returns error | `{ location: 'hero', error: string }` |

### Analytics Utility (lib/analytics.ts)

```typescript
declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export function trackEvent(action: string, params?: Record<string, unknown>) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, params);
  }
}
```

---

## Page Sections (Per Spec)

### 1. Navbar
- Logo: "PrepPilot" text
- Right: "Join Beta" button → scrolls to hero

### 2. Hero Section
- **Badge**: "Finally: A Meal Planner for Histamine Intolerance"
- **Headline**: "Cook Fresh. Stay Safe."
- **Subheadline**: "The first meal planner that tracks **ingredient age** in real-time..."
- **CTA**: Email input + "Request Early Access" button
- **Social Proof**: "Smart inventory tracking for Low-Histamine & MAST diets."

### 3. Problem Section
Three cards with icons:
1. `ShoppingBag` - "Ingredients Age Quickly"
2. `AlertTriangle` - "Waste & Fear"
3. `CalendarClock` - "Poor Planning"

### 4. Solution Section
Three features:
1. "Smart Ingredient Tracking"
2. "Freshness-Based Recipes"
3. "Strict Exclusion Filters"

### 5. How It Works
Visual "Digital Pantry List" showing:
- "Fresh Salmon" → "Use within 12 hours" (orange)
- "Zucchini" → "Safe for 3 days" (green)

### 6. Footer
- Copyright: "© 2025 PrepPilot"
- Disclaimer: "PrepPilot is a concept in development."

---

## Animation Strategy

### Dependencies

```bash
npm install framer-motion
```

### Patterns

```tsx
// Fade up on scroll into view
<motion.div
  initial={{ opacity: 0, y: 20 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  transition={{ duration: 0.6 }}
>
```

### Animations by Section

| Section | Animation |
|---------|-----------|
| Hero | Fade up headline, scale badge |
| Problem cards | Stagger fade up (0.15s delay each) |
| Solution features | Fade up on scroll |
| Pantry mockup | Stagger items with timer animation |
| Success message | Scale in |

---

## Responsive Design

### Breakpoints

| Size | Width | Layout |
|------|-------|--------|
| Mobile | < 640px | Single column, stacked form |
| Tablet | 640-1024px | 2-column cards |
| Desktop | > 1024px | 3-column cards, inline form |

### Key Patterns

```tsx
// Container
className="container mx-auto px-4 sm:px-6 lg:px-8"

// Card grid
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"

// Form
className="flex flex-col sm:flex-row gap-3"
```

---

## Implementation Steps

### Phase 1: Foundation
1. Install `framer-motion`
2. Add sage/alert colors to `globals.css` and `tailwind.config.ts`
3. Create `lib/analytics.ts`
4. Add environment variables to `.env.local`

### Phase 2: Server-Side API
5. Create `app/api/waitlist/route.ts` (Formspree proxy)
6. Create `hooks/use-email-submit.ts`

### Phase 3: Mode Switching
7. Extract current redirect logic to `components/live-mode-redirect.tsx`
8. Update `src/app/page.tsx` with mode-switching logic

### Phase 4: Landing Components
9. Create `components/landing/navbar.tsx`
10. Create `components/landing/email-capture-form.tsx`
11. Create `components/landing/hero-section.tsx`
12. Create `components/landing/problem-section.tsx`
13. Create `components/landing/solution-section.tsx`
14. Create `components/landing/how-it-works-section.tsx`
15. Create `components/landing/landing-footer.tsx`
16. Create `components/landing/landing-page.tsx` (assembles all sections)

### Phase 5: Integration
17. Add GA script to `layout.tsx`
18. Wire up GA events in form and navbar
19. Update metadata for landing page

### Phase 6: Branding Assets (Generated)
20. Create logo SVG (`/public/images/logo.svg`) - "PrepPilot" wordmark with leaf icon in sage green
21. Create logo icon SVG (`/public/images/logo-icon.svg`) - Standalone leaf/checkmark icon
22. Create OG image (`/public/images/og-image.png`) - 1200x630, sage gradient background with logo and tagline
23. Create favicon (`/public/favicon.ico`) - 32x32 sage green icon
24. Create apple-touch-icon (`/public/apple-touch-icon.png`) - 180x180 icon
25. Update PWA icons (`/public/icons/`) - 192x192 and 512x512 versions

### Phase 7: Testing
26. Test pretotype mode end-to-end
27. Test live mode still works
28. Verify Formspree submissions via API proxy
29. Verify GA events in Real-Time

---

## Environment Variables Summary

```bash
# .env.local

# Mode switching (client-side)
NEXT_PUBLIC_APP_MODE=pretotype           # "pretotype" | "live"

# Google Analytics (client-side)
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXX

# Formspree (server-side only - no NEXT_PUBLIC prefix)
FORMSPREE_FORM_ID=xxxxx

# Existing
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Verification Checklist

### Functional
- [ ] Mode switching works via env variable (no code changes)
- [ ] Email form submits via `/api/waitlist` to Formspree
- [ ] Loading spinner shows for 1.5s minimum
- [ ] Success message displays after submission
- [ ] "Join Beta" button scrolls to hero
- [ ] GA events fire for all CTAs

### Visual
- [ ] Sage green primary color applied
- [ ] Alert orange used for urgency elements
- [ ] Responsive on mobile (375px), tablet (768px), desktop (1280px)
- [ ] Animations smooth and subtle

### Integration
- [ ] Formspree dashboard shows submissions
- [ ] GA Real-Time shows page views and events
- [ ] OG image displays correctly (test with opengraph.xyz)
- [ ] Favicon shows in browser tab

### Mode Switching
- [ ] `NEXT_PUBLIC_APP_MODE=pretotype` → landing page at `/`
- [ ] `NEXT_PUBLIC_APP_MODE=live` → redirect to dashboard/login at `/`
- [ ] Switching modes requires only env change + restart

### Security
- [ ] Formspree ID is NOT exposed in client-side code
- [ ] API route validates email format
- [ ] API route handles errors gracefully

---

## Critical Files

- [page.tsx](frontend/src/app/page.tsx) - Mode switching logic
- [layout.tsx](frontend/src/app/layout.tsx) - GA script, metadata
- [globals.css](frontend/src/app/globals.css) - Color variables
- [tailwind.config.ts](frontend/tailwind.config.ts) - Color palette
- [button.tsx](frontend/src/components/ui/button.tsx) - Component pattern reference
