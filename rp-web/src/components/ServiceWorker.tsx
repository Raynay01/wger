'use client';

import { useEffect } from 'react';

/** Registers the service worker that shows the offline page (public/sw.js) */
export function ServiceWorker() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' }).catch(() => {
        // Without it the site works as before, only without the offline page
      });
    }
  }, []);
  return null;
}
