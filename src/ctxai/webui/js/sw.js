const CACHE_NAME = "ctxai-v1";
const OFFLINE_URL = "/js/offline.html";

// Assets to pre-cache for offline support
const PRECACHE_ASSETS = [
  "/",
  "/js/offline.html",
  "/index.css",
  "/css/messages.css",
  "/css/buttons.css",
  "/css/toast.css",
  "/vendor/bootstrap/bootstrap.bundle.min.js",
  "/vendor/google/google-icons.css",
  "/vendor/google/google-icons.ttf",
  "/vendor/dompurify.min.js",
  "/vendor/marked/marked.esm.js",
  "/public/favicon.svg",
];

// Install — pre-cache essential assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }),
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      );
    }),
  );
  self.clients.claim();
});

// Fetch — network-first for API/navigation, cache-first for assets
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin
  if (request.method !== "GET" || url.origin !== location.origin) {
    return;
  }

  // API calls — network only, no caching
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/poll")) {
    return;
  }

  // Socket.IO — pass through
  if (url.pathname.startsWith("/socket.io/")) {
    return;
  }

  // Navigation requests — network-first with offline fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match(OFFLINE_URL);
      }),
    );
    return;
  }

  // Static assets — stale-while-revalidate
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);

      return cached || fetchPromise;
    }),
  );
});
