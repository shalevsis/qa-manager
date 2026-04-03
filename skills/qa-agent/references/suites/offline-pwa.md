# Offline / PWA Test Suite

## When to apply
Use when the app includes a service worker, manifest, background sync, or push notifications. Also apply when offline UX or installability are stated requirements.

## What to test
- Service worker is registered successfully on first page load
- Cached static assets (shell, JS, CSS) are served from cache when the network is offline
- API requests that fail offline show a graceful fallback UI (not a blank screen or unhandled error)
- Requests made while offline are queued and replayed via background sync when connectivity resumes
- Push notification subscription persists across app restarts (not lost on page refresh)
- Install prompt (`beforeinstallprompt`) is shown on eligible browsers after engagement criteria met
- App shell loads instantly on a repeat visit (cache-first, no network round-trip required)
- Deploying a new version invalidates the old cache and the updated assets are served
- Service worker update flow: new worker waits, activates on next load or `skipWaiting` call

## Key patterns

**Service worker registration**
```
// After page load
const reg = await navigator.serviceWorker.getRegistration('/')
assert reg !== undefined
assert reg.active !== null
```

**Offline cache hit**
```
// In test: intercept fetch or use sw-test-utils
goOffline()
const response = await fetch('/app-shell.html')
assert response.ok
assert response.headers.get('x-from-cache') === 'true'  // or check source
```

**Offline API fallback**
```
goOffline()
triggerDataFetch()
await waitFor(() => screen.getByTestId('offline-banner'))
// Assert: no unhandled promise rejection
```

**Background sync queue**
```
goOffline()
submitForm(data)
// Assert: request queued (IndexedDB or sw workbox queue)
goOnline()
await waitForSync()
assert serverReceived(data)
```

**Cache invalidation on deploy**
```
// Bump CACHE_VERSION / service worker file hash
registerUpdatedSW()
await sw.activate()
const keys = await caches.keys()
assert !keys.includes('cache-v1')   // old cache removed
assert keys.includes('cache-v2')
```

**Install prompt**
```
const prompt = await captureEvent('beforeinstallprompt')
assert prompt !== undefined
prompt.prompt()
const { outcome } = await prompt.userChoice
assert ['accepted','dismissed'].includes(outcome)
```

## Common gaps
- Service worker tested only for registration, never for actual offline cache behavior
- Background sync test does not verify the queued request is actually replayed after reconnection
- Push subscription tested only on fresh install — not verified to survive `localStorage.clear()` or app restart
- Cache invalidation: old cache keys checked but stale assets still returned because `activate` event fetch not intercepted
- Install prompt eligibility criteria (HTTPS, manifest, engagement) not verified in test environment — prompt never fires
- App shell load time measured with DevTools manually, not automated with Lighthouse or `PerformanceObserver`
