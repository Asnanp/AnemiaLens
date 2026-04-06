/**
 * Service Worker registration utility for AnemiaLens PWA.
 *
 * - Registers the service worker in production (skips in dev/HMR)
 * - Handles updates (prompts user when a new version is available)
 * - Handles online/offline events
 * - Provides helpers for push notification subscription
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SWMessage =
  | { type: 'SYNC_OFFLINE_QUEUE' }
  | { type: 'SKIP_WAITING' }
  | { type: 'QUEUE_OFFLINE_SUBMISSION'; data: OfflineSubmission };

export interface OfflineSubmission {
  endpoint: string;
  method?: string;
  payload: Record<string, unknown>;
}

export interface OfflineQueueSyncEvent {
  type: 'OFFLINE_QUEUE_SYNCED';
  synced: number;
  remaining: number;
}

export type RegistrationResult =
  | { status: 'skipped'; reason: string }
  | { status: 'registered'; registration: ServiceWorkerRegistration }
  | { status: 'error'; error: string };

// ---------------------------------------------------------------------------
// Main registration
// ---------------------------------------------------------------------------

/**
 * Register the service worker. Only runs in production builds.
 * Returns a result object indicating what happened.
 */
export async function registerServiceWorker(): Promise<RegistrationResult> {
  // Skip in development -- Vite HMR conflicts with SW
  if (import.meta.env.DEV) {
    return { status: 'skipped', reason: 'DEV mode' };
  }

  if (!('serviceWorker' in navigator)) {
    return { status: 'skipped', reason: 'Service Workers not supported' };
  }

  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/',
    });

    setupUpdateHandler(registration);
    setupOnlineOfflineListeners();
    setupMessageListener();

    return { status: 'registered', registration };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('[SW] Registration failed:', message);
    return { status: 'error', error: message };
  }
}

// ---------------------------------------------------------------------------
// Update handling
// ---------------------------------------------------------------------------

/**
 * Listen for the `updatefound` event. When a new SW installs and enters the
 * `installed` state (meaning it has finished downloading), check with the user
 * whether to activate it.
 */
function setupUpdateHandler(registration: ServiceWorkerRegistration) {
  registration.addEventListener('updatefound', () => {
    const newWorker = registration.installing;
    if (!newWorker) return;

    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // New content available -- notify the app
        dispatchCustomEvent('sw-update-available');

        // Auto-activate if the page is idle (no user interaction for 60s)
        // For now, just fire the event; the UI can call skipWaiting()
        console.info('[SW] Update available. Call skipWaiting() to activate.');
      }
    });
  });
}

/**
 * Tell the waiting service worker to activate immediately.
 * Call this after the user confirms they want to update.
 */
export function skipWaiting(): void {
  const reg = window.navigator.serviceWorker?.controller;
  if (!reg) return;

  // Send message to the active worker to forward to waiting worker
  navigator.serviceWorker.ready.then((registration) => {
    if (registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  });
}

// ---------------------------------------------------------------------------
// Online / Offline listeners
// ---------------------------------------------------------------------------

function setupOnlineOfflineListeners() {
  window.addEventListener('online', () => {
    dispatchCustomEvent('sw-online');
    // Trigger offline queue sync
    navigator.serviceWorker.ready.then((registration) => {
      if (registration.active) {
        registration.active.postMessage({ type: 'SYNC_OFFLINE_QUEUE' });
      }
    });
  });

  window.addEventListener('offline', () => {
    dispatchCustomEvent('sw-offline');
  });
}

/**
 * Returns the current online status.
 */
export function isOnline(): boolean {
  return navigator.onLine;
}

// ---------------------------------------------------------------------------
// Message listener (from SW -> page)
// ---------------------------------------------------------------------------

function setupMessageListener() {
  navigator.serviceWorker.addEventListener('message', (event: MessageEvent) => {
    const data = event.data as OfflineQueueSyncEvent | Record<string, unknown>;
    if (data?.type === 'OFFLINE_QUEUE_SYNCED') {
      dispatchCustomEvent('sw-offline-queue-synced', {
        synced: (data as OfflineQueueSyncEvent).synced,
        remaining: (data as OfflineQueueSyncEvent).remaining,
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Offline queue helper
// ---------------------------------------------------------------------------

/**
 * Queue a form submission for later sync when offline.
 */
export function queueOfflineSubmission(submission: OfflineSubmission): void {
  const reg = navigator.serviceWorker.controller;
  if (reg) {
    reg.postMessage({ type: 'QUEUE_OFFLINE_SUBMISSION', data: submission });
  } else {
    // Fallback: store directly in localStorage
    try {
      const queue = JSON.parse(localStorage.getItem('anemia-lens-offline-queue') || '[]');
      queue.push({ timestamp: Date.now(), data: submission });
      localStorage.setItem('anemia-lens-offline-queue', JSON.stringify(queue));
    } catch (err) {
      console.warn('[SW] Failed to queue offline submission:', err);
    }
  }
}

// ---------------------------------------------------------------------------
// Push notifications
// ---------------------------------------------------------------------------

/**
 * Request notification permission and subscribe to push notifications.
 * Returns the subscription or null if permission denied / not supported.
 */
export async function subscribePushNotifications(
  vapidPublicKey?: string
): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('[SW] Push notifications not supported');
    return null;
  }

  // Request permission
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    console.info('[SW] Notification permission denied');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.ready;

    // Check for existing subscription
    const existing = await registration.pushManager.getSubscription();
    if (existing) return existing;

    // Create new subscription
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidPublicKey
        ? (urlBase64ToUint8Array(vapidPublicKey) as BufferSource)
        : undefined,
    });

    return subscription;
  } catch (err) {
    console.error('[SW] Push subscription failed:', err);
    return null;
  }
}

/**
 * Unsubscribe from push notifications.
 */
export async function unsubscribePushNotifications(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false;

  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      return subscription.unsubscribe();
    }
    return false;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function dispatchCustomEvent(name: string, detail?: Record<string, unknown>) {
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

/**
 * Convert a VAPID key from URL-safe base64 to a Uint8Array.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
