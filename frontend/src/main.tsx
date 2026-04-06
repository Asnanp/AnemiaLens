import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './i18n';
import './styles.css';
import './styles-premium.css';
import { registerServiceWorker, isOnline } from './utils/registerServiceWorker';

// ---------------------------------------------------------------------------
// Offline detection: expose global state
// ---------------------------------------------------------------------------

/**
 * Whether the app is currently online.
 * Components can read this directly or listen for `sw-online` / `sw-offline` events.
 */
export let appIsOnline = isOnline();

window.addEventListener('online', () => {
  appIsOnline = true;
});

window.addEventListener('offline', () => {
  appIsOnline = false;
});

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker after the app mounts (non-blocking)
registerServiceWorker().then((result) => {
  if (result.status === 'registered') {
    console.info('[PWA] Service worker registered.');
  } else if (result.status === 'error') {
    console.error('[PWA] Service worker registration error:', result.error);
  } else {
    console.info('[PWA] Service worker skipped:', result.reason);
  }
});
