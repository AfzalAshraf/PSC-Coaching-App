const CACHE_NAME = "kerala-psc-coach-shell-v1";
const APP_FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/app.css",
  "./js/app.js",
  "./js/core.js",
  "./js/math.js",
  "./js/ai.js",
  "./data/starter-bank.json",
  "./icons/icon.svg",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((name) => name.startsWith("kerala-psc-coach-") && name !== CACHE_NAME).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then(async (response) => {
        if (response.ok) await caches.open(CACHE_NAME).then((cache) => cache.put("./index.html", response.clone()));
        return response;
      }).catch(() => caches.match("./index.html"))
    );
    return;
  }

  const refresh = fetch(request).then((response) => {
    if (response.ok && response.type === "basic") {
      return caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone())).then(() => response);
    }
    return response;
  });
  event.waitUntil(refresh.then(() => undefined).catch(() => undefined));
  event.respondWith((async () => {
    const cached = await caches.match(request);
    return cached || refresh;
  })());
});
