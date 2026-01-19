const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://preppilot.com';

interface JsonLdProps {
  type: 'organization' | 'website' | 'product' | 'faq';
}

export function JsonLd({ type }: JsonLdProps) {
  const schemas: Record<string, object> = {
    organization: {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: 'PrepPilot',
      url: BASE_URL,
      logo: `${BASE_URL}/icons/icon-512x512.png`,
      description:
        'The first meal planner that tracks ingredient age in real-time for Low-Histamine & MAST diets.',
      sameAs: [],
      contactPoint: {
        '@type': 'ContactPoint',
        contactType: 'customer support',
        url: BASE_URL,
      },
    },
    website: {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'PrepPilot',
      url: BASE_URL,
      description:
        'Smart meal planning with real-time ingredient freshness tracking for dietary restrictions.',
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: `${BASE_URL}/recipes?ingredient={search_term_string}`,
        },
        'query-input': 'required name=search_term_string',
      },
    },
    product: {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'PrepPilot',
      applicationCategory: 'HealthApplication',
      operatingSystem: 'Web',
      description:
        'The first meal planner that tracks ingredient age in real-time. We prioritize your recipes based on what\'s in your fridge, so you use food before histamine levels rise.',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        availability: 'https://schema.org/ComingSoon',
      },
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: '5',
        ratingCount: '1',
        bestRating: '5',
        worstRating: '1',
      },
      featureList: [
        'Real-time ingredient freshness tracking',
        'Low-histamine diet support',
        'MAST cell diet support',
        'Smart recipe prioritization',
        'Meal prep planning',
        'Food waste reduction',
      ],
    },
    faq: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'What is PrepPilot?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'PrepPilot is a smart meal planning app that tracks ingredient age in real-time, helping you use food before histamine levels rise. It\'s designed specifically for people following Low-Histamine and MAST cell diets.',
          },
        },
        {
          '@type': 'Question',
          name: 'How does ingredient freshness tracking work?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'PrepPilot monitors when you add ingredients to your fridge and calculates their freshness based on food safety guidelines. It then prioritizes recipes that use ingredients before they age, helping reduce food waste and keep meals fresh.',
          },
        },
        {
          '@type': 'Question',
          name: 'Is PrepPilot free?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'PrepPilot is currently in development. Join our waitlist to be notified when we launch and to receive early access pricing.',
          },
        },
        {
          '@type': 'Question',
          name: 'What diets does PrepPilot support?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'PrepPilot is designed specifically for Low-Histamine and MAST cell activation syndrome (MCAS) diets, with features tailored to track ingredient freshness which is crucial for these dietary restrictions.',
          },
        },
      ],
    },
  };

  const schema = schemas[type];
  if (!schema) return null;

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export function LandingPageJsonLd() {
  return (
    <>
      <JsonLd type="organization" />
      <JsonLd type="website" />
      <JsonLd type="product" />
      <JsonLd type="faq" />
    </>
  );
}
