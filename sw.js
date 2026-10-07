// Comic Shelf service worker: app shell + vendored pdf.js cached for offline use.
// Comics themselves live in IndexedDB and are never fetched over the network.
const VERSION = 'cr-v17';
const CORE = ['./', './index.html', './manifest.webmanifest', './vendor/pdf.min.mjs', './vendor/pdf.worker.min.mjs',
  './icons/apple-touch-icon.png', './icons/icon-192.png', './icons/icon-512.png', './icons/icon.svg', './icons/favicon-32.png', './icons/favicon-16.png', './icons/icon-maskable-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // never touch Google sign-in / Picker / Drive API traffic (or anything else cross-origin): straight to the network, never cached
  if (url.origin !== location.origin || /(^|\.)(google|googleapis|gstatic|googleusercontent)\.com$/.test(url.hostname)) return;
  if (req.mode === 'navigate' || url.pathname.endsWith('/index.html') || url.pathname.endsWith('/')) {
    // network-first for the page so updates arrive; cached copy when offline
    e.respondWith(fetch(req, {cache:'no-store'}).then(r => { if (r.ok) { const cp = r.clone(); caches.open(VERSION).then(c => c.put('./index.html', cp)); } return r; })
      .catch(() => caches.match('./index.html', { ignoreSearch: true })));
    return;
  }
  // cache-first for vendored assets (pdf.js, font, cmaps, icons), filled on demand
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req).then(r => {
    if (r.ok && r.type === 'basic') { const cp = r.clone(); caches.open(VERSION).then(c => c.put(req, cp)); } return r; })));
});
