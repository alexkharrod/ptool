// ptool Service Worker — network-first strategy
// All requests go to the network; cache is only used as a fallback.
const CACHE_NAME = 'ptool-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first: always try the network, fall back to cache only for GET requests
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return; // Never intercept POST/mutations
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
