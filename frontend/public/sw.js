/* eslint-disable no-restricted-globals */

/**
 * AnemiaLens Service Worker
 * - Caches static assets for offline support
 * - Network-first strategy for API responses
 * - Offline intake form: saves to localStorage, syncs when online
 * - Push notification support
 */

const CACHE_NAME = 'anemia-lens-v1';
const API_CACHE_NAME = 'anemia-lens-api-v1';
const OFFLINE_QUEUE_KEY = 'anemia-lens-offline-queue';

// Static assets to precache
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/social-card.svg',
];

// ---------------------------------------------------------------------------
// Install: precache static assets
// ---------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
      .catch((err) => console.warn('[SW] Precache failed:', err))
  );
  self.skipWaiting();
});

// ---------------------------------------------------------------------------
// Activate: clean up old caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== API_CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// ---------------------------------------------------------------------------
// Fetch: strategy selection
// ---------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle http/https
  if (!/^https?:$/i.test(url.protocol)) return;

  // API requests -> network-first
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/rest')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Navigation requests -> stale-while-revalidate with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(navigateFallback(request));
    return;
  }

  // Static assets -> cache-first
  event.respondWith(cacheFirst(request));
});

// ---------------------------------------------------------------------------
// Message: handle offline queue sync trigger
// ---------------------------------------------------------------------------
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SYNC_OFFLINE_QUEUE') {
    syncOfflineQueue();
  }
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// ---------------------------------------------------------------------------
// Push: show notification
// ---------------------------------------------------------------------------
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'AnemiaLens';
  const options = {
    body: data.body || 'You have a new notification.',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    tag: data.tag || 'default',
    data: data.data || {},
    actions: data.actions || [],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ---------------------------------------------------------------------------
// Notification click: open relevant page
// ---------------------------------------------------------------------------
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Focus existing window if open
      for (const client of clientList) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow(urlToOpen);
    })
  );
});

// ---------------------------------------------------------------------------
// Online/offline: auto-sync offline queue
// ---------------------------------------------------------------------------
self.addEventListener('online', () => {
  syncOfflineQueue();
});

// ===========================================================================
// Strategies
// ===========================================================================

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Return offline fallback for navigations
    return caches.match('/index.html');
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE_NAME);
      // Clone and cache successful API responses
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Network unavailable -> serve from cache
    const cached = await caches.match(request);
    if (cached) return cached;

    // If no cache, return a minimal offline JSON response
    return new Response(
      JSON.stringify({ error: 'offline', message: 'You are offline. API requests will be queued.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function navigateFallback(request) {
  // Try network first, fall back to cache, then to offline HTML
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return caches.match('/index.html') || Response.error();
  }
}

// ===========================================================================
// Offline Queue (intake form submissions)
// ===========================================================================

/**
 * Queue a submission for later sync.
 * Called from the client via postMessage or directly stored in localStorage.
 */
function queueOfflineSubmission(data) {
  try {
    const queue = JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
    queue.push({ timestamp: Date.now(), data });
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
  } catch (err) {
    console.warn('[SW] Failed to queue offline submission:', err);
  }
}

/**
 * Flush the offline queue by replaying submissions to the API.
 */
async function syncOfflineQueue() {
  let queue;
  try {
    const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
    if (!raw) return;
    queue = JSON.parse(raw);
  } catch {
    return;
  }

  if (!queue.length) return;

  const remaining = [];
  for (const item of queue) {
    try {
      const { endpoint, payload, method } = item.data || {};
      if (!endpoint) {
        continue; // skip malformed entries
      }

      const response = await fetch(endpoint, {
        method: method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload || {}),
      });

      if (!response.ok) {
        remaining.push(item); // keep for retry
      }
    } catch {
      remaining.push(item); // keep for retry
    }
  }

  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(remaining));

  // Notify clients about sync result
  self.clients.matchAll({ includeUncontrolled: true }).then((clients) => {
    for (const client of clients) {
      client.postMessage({
        type: 'OFFLINE_QUEUE_SYNCED',
        synced: queue.length - remaining.length,
        remaining: remaining.length,
      });
    }
  });
}

// Expose queue functions to window via client messaging
self.addEventListener('message', (event) => {
  const { type, data } = event.data || {};
  if (type === 'QUEUE_OFFLINE_SUBMISSION') {
    queueOfflineSubmission(data);
    event.ports?.[0]?.postMessage({ queued: true });
  }
});
