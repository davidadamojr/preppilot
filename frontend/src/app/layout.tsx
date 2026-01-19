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
  title: APP_MODE === 'pretotype'
    ? "PrepPilot - Cook Fresh. Stay Safe."
    : "PrepPilot - Smart Meal Prep Planning",
  description: APP_MODE === 'pretotype'
    ? "The first meal planner that tracks ingredient age in real-time. We prioritize your recipes based on what's in your fridge, so you use food before histamine levels rise."
    : "Adaptive meal prep planning for dietary restrictions",
  manifest: "/manifest.json",
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'https://preppilot.com'),
  openGraph: APP_MODE === 'pretotype' ? {
    title: "PrepPilot - Cook Fresh. Stay Safe.",
    description: "The first meal planner that tracks ingredient age in real-time for Low-Histamine & MAST diets.",
    images: [
      {
        url: '/images/og-image.png',
        width: 1200,
        height: 630,
        alt: 'PrepPilot - Smart Food Freshness Tracking',
      },
    ],
    type: 'website',
  } : undefined,
  twitter: APP_MODE === 'pretotype' ? {
    card: 'summary_large_image',
    title: "PrepPilot - Cook Fresh. Stay Safe.",
    description: "The first meal planner that tracks ingredient age in real-time.",
    images: ['/images/og-image.png'],
  } : undefined,
  appleWebApp: {
    statusBarStyle: "default",
    title: "PrepPilot",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export const viewport: Viewport = {
  themeColor: "#10b981",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
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
