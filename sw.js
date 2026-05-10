// Service Worker - Yiğit Gülyurt Portfolyo
/* global VERSION */
const STATIC_CACHE = `yg-static-v${VERSION}`;
const JS_CACHE     = `yg-js-v${VERSION}`;
const CSS_CACHE    = `yg-css-v${VERSION}`;

// ── Statik dosyalar (İkonlar & Resimler) ───────────────────────────────────
const STATIC_ASSETS = [
    '/static/image/yigitgulyurt/favicon.ico'
];

// ── Sayfa URL'leri ───────────────────────────────────────────────────────────
const PAGE_ASSETS = [
    '/',
    '/hakkimda',
    '/cv',
    '/projeler',
    '/blog',
    '/iletisim',
    '/Mustafa-Kemal-Ataturk',
    '/offline'
];

// ── Subdomain Dosyaları (js. ve css.yigitgulyurt.net.tr) ───────────────────
const JS_ASSETS = [
    'https://js.yigitgulyurt.net.tr/yigitgulyurt/main.yigitgulyurt.js',
    'https://js.yigitgulyurt.net.tr/yigitgulyurt/toastify.yigitgulyurt.js'
];

const CSS_ASSETS = [
    'https://css.yigitgulyurt.net.tr/yigitgulyurt/main.yigitgulyurt.css',
    'https://css.yigitgulyurt.net.tr/yigitgulyurt/toastify.yigitgulyurt.css'
];

// Request objelerine çevir (cross-origin için zorunlu)
const JS_REQUESTS = JS_ASSETS.map(url => new Request(url, { mode: 'cors', credentials: 'omit' }));
const CSS_REQUESTS = CSS_ASSETS.map(url => new Request(url, { mode: 'cors', credentials: 'omit' }));

// ── Hiç önbelleğe alınmayacak URL'ler ──────────────────────────────────────
const NO_CACHE_URLS = [
    '/admin/',
    '/obsidian/',
    '/stream/status'
];

// Yükleme (Install)
self.addEventListener('install', (event) => {
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE).then(cache => cache.addAll([...STATIC_ASSETS, ...PAGE_ASSETS])),
            caches.open(JS_CACHE).then(cache => cache.addAll(JS_REQUESTS)),
            caches.open(CSS_CACHE).then(cache => cache.addAll(CSS_REQUESTS))
        ]).then(() => self.skipWaiting())
    );
});

// Aktifleştirme (Activate)
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            const allowedCaches = [STATIC_CACHE, JS_CACHE, CSS_CACHE];
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (!allowedCaches.includes(cacheName)) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// İstekleri Yakalama (Fetch)
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);

    // Font ve admin bypass
    if (
        url.hostname === 'font.yigitgulyurt.net.tr' ||
        url.pathname.startsWith('/admin') ||
        url.pathname.startsWith('/obsidian')
    ) {
        return;
    }

    // Hiç cache'lenmeyecek URL'ler
    if (NO_CACHE_URLS.some(p => url.pathname.startsWith(p))) {
        event.respondWith(fetch(event.request));
        return;
    }

    // JS ve CSS subdomain yönetimi
    if (url.hostname === 'js.yigitgulyurt.net.tr' || url.hostname === 'css.yigitgulyurt.net.tr') {
        const targetCache = url.hostname === 'js.yigitgulyurt.net.tr' ? JS_CACHE : CSS_CACHE;
        event.respondWith(
            caches.match(event.request, { ignoreSearch: true }).then((cached) => {
                const fetchPromise = fetch(event.request, { mode: 'cors', credentials: 'omit' })
                    .then((network) => {
                        if (network && network.ok) {
                            caches.open(targetCache).then(cache => cache.put(event.request, network.clone()));
                        }
                        return network;
                    })
                    .catch(() => cached);
                return cached || fetchPromise;
            })
        );
        return;
    }

    // Sayfa navigasyonu (Network-First)
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (response.ok && response.status === 200) {
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, response.clone()));
                    }
                    return response;
                })
                .catch(async () => {
                    const cached = await caches.match(event.request);
                    if (cached) return cached;
                    return caches.match('/offline');
                })
        );
        return;
    }

    // Genel statik dosyalar (Stale-While-Revalidate)
    event.respondWith(
        caches.match(event.request, { ignoreSearch: true }).then((cached) => {
            const fetchPromise = fetch(event.request)
                .then((network) => {
                    if (network && network.ok) {
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, network.clone()));
                    }
                    return network;
                })
                .catch(() => cached);
            return cached || fetchPromise;
        })
    );
});
