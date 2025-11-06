const STATIC_CACHE = 'womcast-pwa-static-v3';
const RUNTIME_CACHE = 'womcast-pwa-runtime-v1';

const scopeUrl = (() => {
  if (self.registration && self.registration.scope) {
    return self.registration.scope;
  }

  const url = new URL(self.location.href);
  url.hash = '';
  url.search = '';
  url.pathname = url.pathname.replace(/service-worker\.js$/i, '');
  return url.href.endsWith('/') ? url.href : `${url.href}/`;
})();

const PRECACHE_PATHS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './App.css',
  './icon.svg',
];

const PRECACHE_URLS = PRECACHE_PATHS.map((path) => new URL(path, scopeUrl).toString());
const PRECACHE_FALLBACK = new URL('./index.html', scopeUrl).toString();
const PRECACHE_ROOT = new URL('./', scopeUrl).toString();
const STATIC_ASSET_PATTERN = /\.(?:css|js|mjs|ts|tsx|jsx|json|woff2?|ttf|png|jpe?g|gif|svg|webp|ico|webmanifest)$/i;

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);

      for (const url of PRECACHE_URLS) {
        try {
          const response = await fetch(url, { cache: 'reload' });
          if (response && response.ok) {
            await cache.put(url, response.clone());
          }
        } catch (error) {
          console.warn('[ServiceWorker] Failed to precache', url, error);
        }
      }
    })(),
  );

  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== RUNTIME_CACHE)
          .map((staleKey) => caches.delete(staleKey)),
      );

      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  if (url.origin !== self.location.origin) {
    return;
  }

  if (STATIC_ASSET_PATTERN.test(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (url.href.startsWith(scopeUrl)) {
    event.respondWith(networkThenCache(request));
  }
});

self.addEventListener('message', (event) => {
  const data = event.data;
  if (!data || typeof data !== 'object') {
    return;
  }

  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (data.type === 'CLEAR_RUNTIME_CACHE') {
    event.waitUntil(caches.delete(RUNTIME_CACHE));
  }
});

async function handleNavigationRequest(request) {
  try {
    const response = await fetch(request);
    if (isCacheable(response)) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }

    const fallback = await cache.match(PRECACHE_FALLBACK);
    if (fallback) {
      return fallback;
    }

    const root = await cache.match(PRECACHE_ROOT);
    if (root) {
      return root;
    }

    throw error;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }

  const response = await fetch(request);
  if (isCacheable(response)) {
    cache.put(request, response.clone());
  }
  return response;
}

async function networkThenCache(request) {
  const cache = await caches.open(RUNTIME_CACHE);

  try {
    const response = await fetch(request);
    if (isCacheable(response)) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }

    throw error;
  }
}

function isCacheable(response) {
  if (!response || !response.ok) {
    return false;
  }

  return response.type === 'basic' || response.type === 'default';
}
