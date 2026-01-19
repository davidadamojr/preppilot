// PrepPilot Service Worker
// Provides offline support with intelligent caching strategies

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `preppilot-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `preppilot-dynamic-${CACHE_VERSION}`;
const API_CACHE = `preppilot-api-${CACHE_VERSION}`;

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/manifest.json',
];

// API routes that can be cached for offline use
const CACHEABLE_API_PATTERNS = [
  /\/api\/recipes/,
  /\/api\/auth\/exclusions/,
];

// API routes that should use network-first strategy
const NETWORK_FIRST_API_PATTERNS = [
  /\/api\/fridge/,
  /\/api\/plans/,
  /\/api\/auth\/me/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            return (
              name.startsWith('preppilot-') &&
              name !== STATIC_CACHE &&
              name !== DYNAMIC_CACHE &&
              name !== API_CACHE
            );
          })
          .map((name) => caches.delete(name))
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - handle requests with appropriate strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests except for API
  if (url.origin !== location.origin && !url.pathname.startsWith('/api')) {
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets and pages
  event.respondWith(handleStaticRequest(request));
});

// Cache-first strategy for static assets
async function handleStaticRequest(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Return cached response and update cache in background
    updateCache(request, DYNAMIC_CACHE);
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match('/offline');
      if (offlineResponse) {
        return offlineResponse;
      }
    }

    throw error;
  }
}

// Network-first with cache fallback for API requests
async function handleApiRequest(request) {
  const url = new URL(request.url);

  // Determine caching strategy based on URL pattern
  const isCacheable = CACHEABLE_API_PATTERNS.some((pattern) =>
    pattern.test(url.pathname)
  );
  const isNetworkFirst = NETWORK_FIRST_API_PATTERNS.some((pattern) =>
    pattern.test(url.pathname)
  );

  if (isCacheable) {
    return handleCacheFirstApi(request);
  }

  if (isNetworkFirst) {
    return handleNetworkFirstApi(request);
  }

  // Default: network only
  return fetch(request);
}

// Cache-first for relatively static API data (recipes, exclusions)
async function handleCacheFirstApi(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Check if cache is fresh (less than 24 hours old)
    const cachedDate = cachedResponse.headers.get('sw-cached-at');
    if (cachedDate) {
      const cacheAge = Date.now() - parseInt(cachedDate, 10);
      const maxAge = 24 * 60 * 60 * 1000; // 24 hours

      if (cacheAge < maxAge) {
        // Update cache in background
        updateApiCache(request);
        return cachedResponse;
      }
    }
  }

  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      await cacheApiResponse(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

// Network-first for dynamic API data (fridge, plans, user profile)
async function handleNetworkFirstApi(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      await cacheApiResponse(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Fall back to cache when offline
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Return a proper offline error response
    return new Response(
      JSON.stringify({
        error: 'offline',
        message: 'You are currently offline. Please check your connection.',
      }),
      {
        status: 503,
        headers: {
          'Content-Type': 'application/json',
          'X-Offline': 'true',
        },
      }
    );
  }
}

// Cache API response with timestamp
async function cacheApiResponse(request, response) {
  const cache = await caches.open(API_CACHE);

  // Clone the response and add a timestamp header
  const headers = new Headers(response.headers);
  headers.set('sw-cached-at', Date.now().toString());

  const cachedResponse = new Response(await response.blob(), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });

  await cache.put(request, cachedResponse);
}

// Update cache in background
async function updateCache(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse);
    }
  } catch (error) {
    // Ignore errors during background update
  }
}

// Update API cache in background
async function updateApiCache(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      await cacheApiResponse(request, networkResponse);
    }
  } catch (error) {
    // Ignore errors during background update
  }
}

// Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('preppilot-'))
            .map((name) => caches.delete(name))
        );
      })
    );
  }
});
