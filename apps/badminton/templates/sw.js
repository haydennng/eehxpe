const CACHE_NAME = 'badminton-cache-v6';
const ASSETS = [
  '/badminton/',
  '/badminton/static/manifest.json',
  '/badminton/static/css/style.css',
  '/badminton/static/js/main.js',
  '/badminton/static/js/chart.min.js',
  '/badminton/static/icons/icon-192.png',
  '/badminton/static/icons/icon-512.png',
  '/badminton/static/icons/maskable-192.png',
  '/badminton/static/icons/maskable-512.png',
  '/badminton/static/offline.html'
];

self.addEventListener('install', event => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Caching app shell');
        return cache.addAll(ASSETS);
      })
      .catch(err => {
        console.log('[SW] Cache install failed:', err);
      })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => {
          console.log('[SW] Removing old cache:', k);
          return caches.delete(k);
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  
  // Only handle GET requests
  if (req.method !== 'GET') return;
  
  // Don't intercept external requests (CDNs, etc.)
  if (url.origin !== location.origin) {
    return;
  }

  // Navigation requests: network-first, fallback to offline page
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .catch(() => caches.match('/badminton/static/offline.html'))
    );
    return;
  }

  // Static assets: network-first, fallback to cache for offline
  event.respondWith(
    fetch(req)
      .then(resp => {
        // Only cache successful responses
        if (resp && resp.status === 200 && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(req, copy);
          });
        }
        return resp;
      })
      .catch(() => {
        // Fallback to cache if network fails (offline mode)
        return caches.match(req)
          .then(cached => {
            if (cached) {
              return cached;
            }
            // If not in cache, show offline page
            return caches.match('/badminton/static/offline.html');
          });
      })
  );
});
