# Request Lifecycle Suite

## When to apply
Apply when the project has component-based UI that fetches data (React, Vue, Angular, Svelte), uses `AbortController` or axios cancel tokens, makes cross-origin requests to a separate API origin, or contains multiple components that might trigger duplicate requests for the same resource. Also apply to any hook, service, or module that owns retry logic, token refresh, or request deduplication.

## What to test

**AbortController / cancellation**
- Navigating away from a page while a request is in-flight cancels the request — no state update on an unmounted component, no console warning about setting state after unmount
- Component unmount cancels all pending requests started by that component, not just the most recent one
- User cancelling an upload or download actually aborts the HTTP request at the network level, not just hides the progress UI
- A cancelled request does not trigger error state, error toasts, or retry logic
- `AbortError` is caught separately from real errors and silently ignored — it is not shown to the user as a failure

**CORS**
- Preflight `OPTIONS` request is handled correctly by the server; a missing or wrong `Access-Control-Allow-Origin` header surfaces a useful error in development rather than a silent failure
- Credentialed requests (cookies, auth headers) include `credentials: 'include'` on the client and the server responds with `Access-Control-Allow-Credentials: true`; requests without credentials do not accidentally send cookies cross-origin
- Preflight cache (`Access-Control-Max-Age`) is set to a reasonable value to avoid a preflight round-trip on every single request

**Request deduplication**
- Two sibling components mounting simultaneously and requesting the same resource produce only one network call, not two identical parallel requests
- Rapid back/forward navigation does not stack multiple in-flight requests for the same route
- Clicking a submit button twice quickly triggers the action only once at the network layer (idempotency guard, not just UI disabling)
- Search input debounce cancels the previous in-flight request before firing the new one; no stale search response can overwrite the current one

**Request ordering / race conditions**
- A stale response from a slow earlier request does not overwrite the result of a newer request (last-request-wins strategy is enforced)
- Sequential async operations complete in logical order even when responses arrive out of order
- Optimistic UI updates are rolled back if the server request fails; rolled-back state matches the pre-optimistic state exactly

**Headers and auth**
- The `Authorization` header is attached to all authenticated requests; no authenticated request is ever sent without it
- Token refresh: a 401 response triggers exactly one token refresh; the original request is retried with the new token; no duplicate refresh calls for parallel 401s
- After logout, in-flight requests that complete do not update app state with stale user data
- Sensitive auth headers are not forwarded to third-party domains via CORS (e.g. analytics or CDN requests must not carry the internal `Authorization` header)

**Request retries**
- Retry logic uses exponential backoff, not a fixed interval
- Retry does not fire on client errors (4xx) — only on network errors and 5xx responses
- Maximum retry count is enforced; the app does not retry forever
- When a `Retry-After` header is present, retry waits for the specified duration rather than using the default backoff interval

## Key patterns

**Assert AbortController signal is passed and request is cancelled on unmount (JS)**
```js
const fetchSpy = vi.spyOn(global, 'fetch')
const { unmount } = render(<DataFetchingComponent />)
expect(fetchSpy).toHaveBeenCalledWith(
  expect.any(String),
  expect.objectContaining({ signal: expect.any(AbortSignal) })
)
unmount()
const signal = fetchSpy.mock.calls[0][1].signal
expect(signal.aborted).toBe(true)
```

**Assert AbortError is not shown as an error toast (JS)**
```js
server.use(http.get('/api/data', async ({ request }) => {
  await new Promise((_, reject) => request.signal.addEventListener('abort', reject))
}))
const { unmount } = render(<DataFetchingComponent />)
unmount()
await waitFor(() => {
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
```

**Assert deduplication — two components, one request (JS — MSW + fetch spy)**
```js
const fetchSpy = vi.spyOn(global, 'fetch')
render(
  <>
    <UserAvatar userId="42" />
    <UserBadge userId="42" />
  </>
)
await screen.findAllByTestId('user-loaded')
expect(fetchSpy).toHaveBeenCalledTimes(1)
```

**Assert deduplication (Python — requests-mock)**
```python
def test_deduplication(requests_mock):
    adapter = requests_mock.get('https://api.example.com/user/42', json={'name': 'Alice'})
    fetch_user(42)
    fetch_user(42)  # second call should hit cache, not the network
    assert adapter.call_count == 1
```

**Race condition — stale response does not overwrite newer result (JS)**
```js
let resolveFirst, resolveSecond
server.use(
  http.get('/api/search', ({ request }) => {
    const q = new URL(request.url).searchParams.get('q')
    if (q === 'slow') return new Promise(r => { resolveFirst = () => r(HttpResponse.json({ results: ['stale'] })) })
    return HttpResponse.json({ results: ['fresh'] })
  })
)
// fire slow query first, then fast query
await userEvent.type(searchInput, 'slow')
await userEvent.clear(searchInput)
await userEvent.type(searchInput, 'fast')
resolveFirst() // slow response arrives after fast
await screen.findByText('fresh')
expect(screen.queryByText('stale')).not.toBeInTheDocument()
```

**Assert token refresh fires once for parallel 401s (JS)**
```js
let refreshCount = 0
vi.spyOn(authService, 'refreshToken').mockImplementation(async () => {
  refreshCount++
  return 'new-token'
})
server.use(http.get('/api/a', () => new HttpResponse(null, { status: 401 })))
server.use(http.get('/api/b', () => new HttpResponse(null, { status: 401 })))
await Promise.all([apiClient.get('/api/a'), apiClient.get('/api/b')])
expect(refreshCount).toBe(1)  // not 2
```

**Assert MSW intercepts request headers (JS)**
```js
let capturedHeaders
server.use(
  http.get('/api/protected', ({ request }) => {
    capturedHeaders = Object.fromEntries(request.headers)
    return HttpResponse.json({ data: 'ok' })
  })
)
await apiClient.get('/api/protected')
expect(capturedHeaders['authorization']).toMatch(/^Bearer /)
```

**Assert retry uses exponential backoff, not fixed interval (JS)**
```js
vi.useFakeTimers()
server.use(http.get('/api/data', () => new HttpResponse(null, { status: 503 })))
fetchWithRetry('/api/data')
await vi.runAllTimersAsync()
const delays = getRetryDelays()   // helper that captures setTimeout durations
expect(delays[1]).toBeGreaterThan(delays[0])  // second wait longer than first
expect(delays[2]).toBeGreaterThan(delays[1])  // third wait longer than second
```

**Assert retry does not fire on 400 (Python)**
```python
def test_no_retry_on_400(httpx_mock, mocker):
    httpx_mock.add_response(status_code=400)
    send_spy = mocker.spy(httpx.Client, 'send')
    with pytest.raises(ClientError):
        api_client.post('/api/items', json={})
    assert send_spy.call_count == 1  # no retry
```

## Common gaps
- `AbortController` is created but `signal` is never passed to `fetch` — the request continues running after unmount
- `AbortError` is caught by the generic error handler and shown as an error toast to the user
- CORS preflight fails silently in the test environment because the test server has no CORS middleware — the bug only appears in staging
- Two sibling components each fetch the same user profile, producing two identical API calls on every page load
- A stale search result overwrites the current result because the in-flight request for the previous query was not cancelled
- Token refresh is triggered once per 401 response — when three requests fail simultaneously, refresh is called three times, invalidating the tokens mid-refresh
- Retry fires on 400 Bad Request — the server receives an identical invalid payload repeatedly until the retry limit is hit
- Optimistic UI update is not rolled back on failure — the UI shows a change that the server rejected
