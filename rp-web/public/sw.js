// Service worker of the installable ALMOVA app. It only stores the "no
// connection" page and its files: pages with health data are never kept on
// the phone, they always come from the server.

const CACHE = 'almova-offline-v1';
const OFFLINE = '/offline.html';
const FILES = [OFFLINE, '/offline.css', '/icon-192.png'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then(cache => cache.addAll(FILES))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', event => {
  // Drops the files of older versions
  event.waitUntil(
    caches
      .keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.mode === 'navigate') {
    // Pages: always from the server; the offline page only when it cannot be reached
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE)));
    return;
  }
  // The offline page's own files, when they are requested without a connection
  const url = new URL(request.url);
  if (url.origin === self.location.origin && FILES.includes(url.pathname)) {
    event.respondWith(fetch(request).catch(() => caches.match(url.pathname)));
  }
});
