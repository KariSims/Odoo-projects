/**
 * Micro Flow — Service Worker Registration
 * Loaded as a web.assets_backend asset.
 * Registers the SW and triggers background sync on reconnection.
 */

(function () {
    if (!('serviceWorker' in navigator)) return;

    navigator.serviceWorker
        .register('/microflow/sw.js', { scope: '/' })
        .then((reg) => {
            // Request persistent storage for IndexedDB offline drafts
            if (navigator.storage && navigator.storage.persist) {
                navigator.storage.persist();
            }

            // Trigger sync when the browser comes back online
            window.addEventListener('online', () => {
                if ('sync' in reg) {
                    reg.sync.register('microflow-sync').catch(() => {});
                }
            });

            // Show offline indicator in Odoo notification bar
            window.addEventListener('offline', () => {
                console.warn('[Micro Flow] Hors ligne — les versements seront synchronisés au retour réseau.');
            });
        })
        .catch((err) => {
            console.error('[Micro Flow] Service worker registration failed:', err);
        });
})();
