import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import Script from "next/script";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/lib/query-provider";
import { Toaster } from "@/components/ui/toaster";
import { ServiceWorkerProvider } from "@/components/providers/service-worker-provider";
import { SkipLink } from "@/components/ui/skip-link";

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://preppilot.io';

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE || 'live';

export const metadata: Metadata = {
  title: {
    default: APP_MODE === 'pretotype'
      ? "PrepPilot - Cook Fresh. Stay Safe. | Low-Histamine Meal Planning"
      : "PrepPilot - Smart Meal Prep Planning",
    template: "%s | PrepPilot",
  },
  description: APP_MODE === 'pretotype'
    ? "The first meal planner that tracks ingredient age in real-time. We prioritize your recipes based on what's in your fridge, so you use food before histamine levels rise. Perfect for Low-Histamine & MAST cell diets."
    : "Adaptive meal prep planning for dietary restrictions",
  manifest: "/manifest.json",
  metadataBase: new URL(BASE_URL),
  alternates: {
    canonical: '/',
  },
  keywords: APP_MODE === 'pretotype' ? [
    'meal planning',
    'low histamine diet',
    'MAST cell diet',
    'MCAS diet',
    'ingredient freshness',
    'food tracking',
    'meal prep',
    'histamine intolerance',
    'food waste reduction',
    'recipe planner',
    'dietary restrictions',
    'fresh ingredients',
    'food safety',
    'meal planner app',
  ] : undefined,
  authors: [{ name: 'PrepPilot' }],
  creator: 'PrepPilot',
  publisher: 'PrepPilot',
  category: 'Health & Fitness',
  classification: 'Meal Planning Application',
  robots: {
    index: APP_MODE === 'pretotype',
    follow: APP_MODE === 'pretotype',
    googleBot: {
      index: APP_MODE === 'pretotype',
      follow: APP_MODE === 'pretotype',
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: APP_MODE === 'pretotype' ? {
    title: "PrepPilot - Cook Fresh. Stay Safe.",
    description: "The first meal planner that tracks ingredient age in real-time for Low-Histamine & MAST diets. Stop food waste, stay safe.",
    url: BASE_URL,
    siteName: 'PrepPilot',
    locale: 'en_US',
    type: 'website',
  } : undefined,
  twitter: APP_MODE === 'pretotype' ? {
    card: 'summary_large_image',
    title: "PrepPilot - Cook Fresh. Stay Safe.",
    description: "The first meal planner that tracks ingredient age in real-time for Low-Histamine & MAST diets.",
    creator: '@preppilot',
    site: '@preppilot',
  } : undefined,
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "PrepPilot",
  },
  formatDetection: {
    telephone: false,
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#10b981' },
    { media: '(prefers-color-scheme: dark)', color: '#059669' },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  colorScheme: 'light',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        {/* Preconnect to external domains for performance */}
        {GA_MEASUREMENT_ID && (
          <>
            <link rel="preconnect" href="https://www.googletagmanager.com" />
            <link rel="preconnect" href="https://www.google-analytics.com" />
            <link rel="dns-prefetch" href="https://www.googletagmanager.com" />
            <link rel="dns-prefetch" href="https://www.google-analytics.com" />
          </>
        )}
        {/* Preconnect to Formspree for waitlist */}
        <link rel="preconnect" href="https://formspree.io" />
        <link rel="dns-prefetch" href="https://formspree.io" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <SkipLink />
        <QueryProvider>
          <AuthProvider>
            <ServiceWorkerProvider>
              {children}
              <Toaster />
            </ServiceWorkerProvider>
          </AuthProvider>
        </QueryProvider>
        {GA_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_MEASUREMENT_ID}');
              `}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
