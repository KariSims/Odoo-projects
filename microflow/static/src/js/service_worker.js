/**
 * Micro Flow — Service Worker (TODO-5)
 * Offline drafts via IndexedDB + cache-first for microflow assets.
 * Registered by sw_register.js on page load.
 */

const CACHE_NAME = 'microflow-v1';
const OFFLINE_STORE = 'microflow-offline-payments';

// Assets to cache for offline access
const PRECACHE_URLS = [
    '/web#action=microflow',
];

// ── Install: pre-cache shell assets ──────────────────────────────────────────
self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRECACHE_URLS).catch(() => {
                // Network may be unavailable during install — that's OK
            });
        })
    );
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});

// ── Fetch: network-first for API calls, cache-first for assets ───────────────
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Only intercept same-origin requests
    if (url.origin !== self.location.origin) return;

    // Micro Flow JSON-RPC calls → network first, queue offline
    if (url.pathname === '/web/dataset/call_kw' || url.pathname === '/web/dataset/call') {
        event.respondWith(networkFirstWithOfflineQueue(event.request));
        return;
    }

    // Static assets → cache first
    if (url.pathname.startsWith('/microflow/static/')) {
        event.respondWith(cacheFirst(event.request));
        return;
    }
});

async function networkFirstWithOfflineQueue(request) {
    try {
        const response = await fetch(request.clone());
        return response;
    } catch (_) {
        // Offline: read body, detect microflow write ops, store in IDB
        try {
            const body = await request.clone().json();
            if (isMicroflowWriteOp(body)) {
                await storeOfflinePayment(body);
                return new Response(
                    JSON.stringify({
                        jsonrpc: '2.0',
                        id: body.id,
                        result: { offline: true, message: 'Enregistré hors ligne — sync au retour réseau.' },
                    }),
                    { headers: { 'Content-Type': 'application/json' } }
                );
            }
        } catch (_) {}
        return new Response(JSON.stringify({ error: 'Hors ligne' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
}

function isMicroflowWriteOp(body) {
    const model = body?.params?.model || '';
    const method = body?.params?.method || '';
    return (
        ['micro.cycle.line', 'micro.transaction', 'micro.credit.line'].includes(model) &&
        ['register_collection', 'register_payment', 'write', 'create'].includes(method)
    );
}

// ── IndexedDB helpers ─────────────────────────────────────────────────────────
function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(OFFLINE_STORE, 1);
        req.onupgradeneeded = (e) => {
            e.target.result.createObjectStore('pending', { autoIncrement: true });
        };
        req.onsuccess = (e) => resolve(e.target.result);
        req.onerror = (e) => reject(e.target.error);
    });
}

async function storeOfflinePayment(payload) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('pending', 'readwrite');
        tx.objectStore('pending').add({ payload, ts: Date.now() });
        tx.oncomplete = resolve;
        tx.onerror = (e) => reject(e.target.error);
    });
}

// ── Sync: replay queued calls when back online ────────────────────────────────
self.addEventListener('sync', async (event) => {
    if (event.tag === 'microflow-sync') {
        event.waitUntil(replayOfflineQueue());
    }
});

async function replayOfflineQueue() {
    const db = await openDB();
    const store = db.transaction('pending', 'readwrite').objectStore('pending');
    const all = await new Promise((res, rej) => {
        const req = store.getAll();
        req.onsuccess = (e) => res(e.target.result);
        req.onerror = (e) => rej(e.target.error);
    });

    for (const item of all) {
        try {
            await fetch('/web/dataset/call_kw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item.payload),
            });
        } catch (_) {
            return; // Still offline — stop replaying
        }
    }
    // Clear successfully replayed items
    db.transaction('pending', 'readwrite').objectStore('pending').clear();
}
