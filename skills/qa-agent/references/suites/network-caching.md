# Network Caching Suite

Detection: `Cache-Control`, `ETag`, `If-None-Match`, `If-Modified-Since`, CDN config files (CloudFront, Cloudflare, nginx cache directives), `stale-while-revalidate`, service worker cache, `react-query`/`swr`/`tanstack-query` with stale time config.

## When to apply
Apply when the project uses HTTP caching headers, a CDN, a client-side data-fetching library with caching (React Query, SWR), or a service worker cache strategy. Caching bugs are silent — the app appears to work but shows stale or wrong data.

## What to test

**HTTP cache headers**
- Response includes correct `Cache-Control` directives for its content type (e.g. `no-store` for private user data, long max-age for static assets)
- `ETag` header present on cacheable responses
- Conditional request with `If-None-Match` returns `304 Not Modified` and app uses cached data
- `stale-while-revalidate` — app shows stale data immediately, revalidates in background, updates UI on fresh response
- `no-cache` — app always revalidates before using cached response
- `private` — user-specific responses not cached by shared/CDN cache
- Immutable assets (content-hashed filenames) have very long `max-age` and `immutable` directive

**Post-auth cache invalidation**
- After logout, cached user data is not served to the next user on the same browser
- After login as a different user, stale responses from the previous session are not shown
- After a write operation (POST/PUT/DELETE), the affected cache entries are invalidated and fresh data is fetched

**Client-side cache (React Query / SWR)**
- `staleTime` configured correctly — data is not re-fetched on every render
- `gcTime` (garbage collect time) — cache is cleaned up after the configured window
- Cache key includes all query parameters — different params produce different cache entries
- Optimistic update is rolled back on error, cache restored to previous state
- Cache is invalidated after a mutation — dependent queries refetch automatically

**CDN behavior**
- Static assets are served with `Cache-Control: public, max-age=31536000, immutable`
- API responses that vary by auth are not cached by CDN (`Vary: Authorization` or `Cache-Control: private`)
- CDN purge tested: after deploying new content, old cached version is not served
- Vary header — responses that vary by `Accept-Language` or `Accept-Encoding` have `Vary` set correctly

**Edge cases**
- Cache poisoning: user-supplied input does not end up as a cache key variation that poisons cache for others
- Large cache — after filling cache to capacity, LRU eviction works correctly and app fetches fresh data
- Offline cache (service worker) — stale cached page served while offline, fresh page served on reconnect
- Cache stampede on cold start — many simultaneous requests to empty cache are deduplicated

## Key patterns

**Assert Cache-Control header in integration test**
```js
// JS (supertest)
const res = await request(app).get('/api/profile')
expect(res.headers['cache-control']).toMatch(/no-store/)

# Python (pytest + requests)
resp = client.get('/api/profile')
assert 'no-store' in resp.headers.get('Cache-Control', '')
```

**Assert 304 on conditional request**
```js
// JS
const first = await request(app).get('/api/items')
const etag = first.headers['etag']
const second = await request(app)
  .get('/api/items')
  .set('If-None-Match', etag)
expect(second.status).toBe(304)
expect(second.body).toEqual({})  // no body on 304

# Python
first = client.get('/api/items')
etag = first.headers['ETag']
second = client.get('/api/items', headers={'If-None-Match': etag})
assert second.status_code == 304
```

**Inspect response headers in Playwright**
```js
const [response] = await Promise.all([
  page.waitForResponse('**/api/items'),
  page.goto('/items'),
])
expect(response.headers()['cache-control']).toContain('public')
expect(response.headers()['etag']).toBeDefined()
```

**React Query — cache key isolation per user**
```js
const { result: result1 } = renderHook(() => useUserData('user-1'), { wrapper })
const { result: result2 } = renderHook(() => useUserData('user-2'), { wrapper })
expect(fetchSpy).toHaveBeenCalledTimes(2)  // separate fetches, not same cached entry
expect(result1.current.name).not.toBe(result2.current.name)
```

**React Query — mutation invalidates dependent query**
```js
const queryClient = new QueryClient()
queryClient.setQueryData(['items'], [{ id: 1, name: 'old' }])
await mutate({ id: 1, name: 'new' })
// after mutation, cache entry for ['items'] should be gone or refreshed
expect(queryClient.getQueryState(['items'])?.isInvalidated).toBe(true)
```

**React Query — optimistic update rollback on error**
```js
server.use(rest.post('/api/items', (req, res, ctx) => res(ctx.status(500))))
userEvent.click(addButton)
expect(screen.getByText('optimistic-item')).toBeInTheDocument()  // shown immediately
await waitFor(() =>
  expect(screen.queryByText('optimistic-item')).not.toBeInTheDocument()  // rolled back
)
```

**SWR — stale data shown then updated**
```js
// JS
const { result } = renderHook(() => useSWR('/api/data', fetcher, { dedupingInterval: 0 }))
expect(result.current.data).toBe('stale')        // served from cache immediately
await waitFor(() => expect(result.current.data).toBe('fresh'))  // updated after revalidation

# Python equivalent: assert cache.get(key) returns old value, then after ttl returns new fetch
```

**Service worker — stale-while-revalidate**
```js
// Playwright
await page.goto('/dashboard')
await page.evaluate(() => navigator.serviceWorker.controller?.postMessage({ type: 'GO_OFFLINE' }))
await page.reload()
// page still renders with cached content
expect(await page.title()).toBe('Dashboard')
await page.evaluate(() => navigator.serviceWorker.controller?.postMessage({ type: 'GO_ONLINE' }))
await page.waitForResponse('**/api/dashboard-data')
// fresh data now visible
```

## Common gaps
- Private user data cached with `Cache-Control: public` — another user on same CDN node sees someone else's data
- After logout, `localStorage` cleared but HTTP cache not — next user sees stale profile data on first load
- React Query cache key does not include user ID — user switching accounts sees previous user's data
- `ETag` returned by server but client never sends `If-None-Match` — always fetches full response
- `staleTime: 0` (default) causes refetch on every component mount — page hammers the API
- Static assets not content-hashed — long `max-age` set but new deploy served to users only after cache expires
- Cache invalidation after mutation only invalidates exact key — related queries (list views) not refreshed
