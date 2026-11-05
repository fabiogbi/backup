/* Service worker: deixa o app abrir e contar sem sinal (depósito sem Wi-Fi).
 * Ao alterar qualquer arquivo do app, aumente VERSAO para forçar atualização. */
const VERSAO = 'inventario-v1';
const ARQUIVOS = [
  './',
  './index.html',
  './styles.css',
  './manifest.webmanifest',
  './js/core.js',
  './js/db.js',
  './js/scanner.js',
  './js/app.js',
  './vendor/zxing.min.js',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(chaves.filter((k) => k !== VERSAO).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  if (new URL(e.request.url).origin !== self.location.origin) return;

  e.respondWith(
    caches.match(e.request).then((emCache) => {
      if (emCache) return emCache;
      return fetch(e.request)
        .then((resp) => {
          if (resp.ok) caches.open(VERSAO).then((c) => c.put(e.request, resp.clone()));
          return resp;
        })
        .catch(() => caches.match('./index.html'));
    })
  );
});
