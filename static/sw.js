// Service Worker for Time Tracker PWA
const CACHE_NAME = 'time-tracker-v2.0.0';
const urlsToCache = [
    '/',
    '/static/manifest.json',
    '/add_order',
    '/reports',
    '/upload_image',
    // External dependencies
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install event - cache resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching files');
                return cache.addAll(urlsToCache);
            })
            .catch(err => {
                console.log('Service Worker: Cache failed', err);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // For page requests, use cache-first strategy
    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                // Return cached version if available
                if (cachedResponse) {
                    return cachedResponse;
                }

                // Otherwise fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache if not a success response
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone the response
                        const responseToCache = response.clone();

                        // Add to cache
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    });
            })
            .catch(() => {
                // If both cache and network fail, show offline message
                if (event.request.destination === 'document') {
                    return new Response(
                        `
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Time Tracker - Offline</title>
                            <meta name="viewport" content="width=device-width, initial-scale=1">
                            <style>
                                body {
                                    font-family: 'Segoe UI', sans-serif;
                                    display: flex;
                                    justify-content: center;
                                    align-items: center;
                                    height: 100vh;
                                    margin: 0;
                                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                                    color: white;
                                    text-align: center;
                                }
                                .offline-container {
                                    max-width: 400px;
                                    padding: 2rem;
                                }
                                .icon {
                                    font-size: 4rem;
                                    margin-bottom: 1rem;
                                }
                                .btn {
                                    background: white;
                                    color: #2563eb;
                                    padding: 0.75rem 1.5rem;
                                    border: none;
                                    border-radius: 8px;
                                    font-weight: 600;
                                    cursor: pointer;
                                    margin-top: 1rem;
                                }
                            </style>
                        </head>
                        <body>
                            <div class="offline-container">
                                <div class="icon">📱</div>
                                <h2>You're Offline</h2>
                                <p>Time Tracker is not available right now. Check your internet connection and try again.</p>
                                <button class="btn" onclick="window.location.reload()">Try Again</button>
                            </div>
                        </body>
                        </html>
                        `,
                        {
                            headers: { 'Content-Type': 'text/html' }
                        }
                    );
                }
            })
    );
});

// Background sync for offline time entries
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync triggered');
    
    if (event.tag === 'time-entry-sync') {
        event.waitUntil(syncTimeEntries());
    }
});

// Push notification handling
self.addEventListener('push', event => {
    console.log('Service Worker: Push received');
    
    const options = {
        body: event.data ? event.data.text() : 'Time Tracker notification',
        icon: '/static/img/icon-192x192.png',
        badge: '/static/img/icon-96x96.png',
        vibrate: [200, 100, 200],
        data: {
            url: '/'
        },
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/static/img/icon-96x96.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Time Tracker', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification clicked');
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});

async function syncTimeEntries() {
    console.log('Service Worker: Syncing offline entries...');
    // Sync logic would go here
} 