# HTTP Status Codes Suite

## When to apply
Apply to any project that uses an HTTP client: `fetch`, `axios`, `requests`, `httpx`, or any wrapper around them. Cover every status class the client can plausibly receive. This includes frontend apps consuming an API, backend services calling third-party APIs, and CLI tools making network requests.

## What to test

**2xx — Success variants**
- 200 OK — standard success; response body parsed and displayed correctly
- 201 Created — resource created; `Location` header is present and points to the new resource
- 202 Accepted — async job started; app enters a polling or progress state, does not treat the job as complete
- 204 No Content — app does not attempt to parse the empty body (no JSON parse crash or silent undefined)
- 206 Partial Content — range request returns the correct byte range; resumable download resumes from the right offset

**3xx — Redirects**
- 301 Moved Permanently / 302 Found — client follows redirect automatically; final URL is correct
- 307 Temporary Redirect / 308 Permanent Redirect — request body (e.g. POST payload) is preserved through the redirect; not silently dropped as it is with 301/302
- Too many redirects — client hits the redirect loop limit; app surfaces an error, does not hang indefinitely
- Redirect to external domain — app handles or intentionally blocks the cross-origin redirect; no silent data leakage via headers

**4xx — Client errors**
- 400 Bad Request — validation error shown to the user with an actionable message identifying what was wrong
- 401 Unauthorized — triggers the re-authentication flow (login redirect, token refresh); does not show a blank page
- 403 Forbidden — treated as distinct from 401: user is authenticated but lacks permission; appropriate "access denied" message shown, not a generic "unauthorized"
- 404 Not Found — app renders a not-found UI; does not crash or show a raw error object
- 405 Method Not Allowed — app does not silently retry with a different method or treat this as a network failure
- 408 Request Timeout — distinguished from a client-side timeout; user is notified with a retry option
- 409 Conflict — concurrent edit or duplicate-creation conflict is surfaced to the user (e.g. "someone else edited this record")
- 410 Gone — resource permanently removed; app does not keep retrying; cached references are invalidated
- 413 Payload Too Large — upload is rejected before completion; user sees a clear size-limit error, not a generic failure
- 415 Unsupported Media Type — incorrect `Content-Type` was sent; app surfaces the error rather than failing silently
- 422 Unprocessable Entity — field-level validation errors from the server are mapped to individual form fields, not collapsed into a single "something went wrong" message
- 429 Too Many Requests — app reads the `Retry-After` header, waits the correct duration before retrying, and shows a rate-limit message to the user
- 451 Unavailable For Legal Reasons — handled gracefully with an explanatory message; does not crash or show a generic error

**5xx — Server errors**
- 500 Internal Server Error — app shows a generic error message; no stack trace or internal detail exposed to the user
- 502 Bad Gateway — treated as transient; retry logic fires with backoff
- 503 Service Unavailable — app shows a maintenance or unavailability message; retries with exponential backoff up to a maximum
- 504 Gateway Timeout — distinguished from an app-level timeout; user sees an appropriate "server took too long" message
- 507 Insufficient Storage — server-side storage full during upload; user is told to try a smaller file or free space
- 511 Network Authentication Required — captive portal scenario detected; user is prompted to authenticate on the network

**Edge cases**
- Empty response body on a non-204 status — app handles missing body without crashing (no `JSON.parse` of an empty string)
- Response with wrong `Content-Type` (e.g. an HTML error page returned instead of JSON) — parser does not crash; error is surfaced usefully
- Status 200 with an error in the body (`{"success": false, "error": "..."}`) — app reads the body, not just the status code, to determine success
- Status code outside any known range (e.g. 0, 999, negative) — app falls back gracefully and does not throw an unhandled exception

## Key patterns

**Mock a specific status code (JS — MSW)**
```js
import { http, HttpResponse } from 'msw'

server.use(
  http.get('/api/resource', () => HttpResponse.json({ error: 'rate limited' }, { status: 429, headers: { 'Retry-After': '5' } }))
)
```

**Mock a specific status code (Python — pytest-httpx)**
```python
def test_rate_limited(httpx_mock):
    httpx_mock.add_response(status_code=429, headers={'Retry-After': '5'})
    result = client.get('/api/resource')
    assert result.status_code == 429
```

**Mock a specific status code (Python — responses library)**
```python
import responses

@responses.activate
def test_server_error():
    responses.add(responses.GET, 'https://api.example.com/data', status=500)
    resp = requests.get('https://api.example.com/data')
    assert resp.status_code == 500
```

**Assert correct UI state per status class (JS)**
```js
// 401 → redirect to login, not blank page
server.use(http.get('/api/me', () => new HttpResponse(null, { status: 401 })))
render(<App />)
await screen.findByRole('heading', { name: /sign in/i })
expect(screen.queryByTestId('dashboard')).not.toBeInTheDocument()

// 403 → permission denied message, not "unauthorized"
server.use(http.get('/api/admin', () => new HttpResponse(null, { status: 403 })))
render(<AdminPage />)
await screen.findByText(/you do not have permission/i)
expect(screen.queryByText(/sign in/i)).not.toBeInTheDocument()
```

**Assert 204 does not cause a parse crash (JS)**
```js
server.use(http.delete('/api/items/1', () => new HttpResponse(null, { status: 204 })))
await expect(deleteItem(1)).resolves.not.toThrow()
```

**Assert retry fires for 429/502/503 but NOT for 400/401/403/404/410 (JS)**
```js
const fetchSpy = vi.spyOn(global, 'fetch')

// 429 — retry should fire
server.use(http.get('/api/data', () => new HttpResponse(null, { status: 429, headers: { 'Retry-After': '1' } })))
await fetchWithRetry('/api/data')
expect(fetchSpy).toHaveBeenCalledTimes(greaterThan(1))

// 404 — no retry
fetchSpy.mockClear()
server.use(http.get('/api/data', () => new HttpResponse(null, { status: 404 })))
await fetchWithRetry('/api/data').catch(() => {})
expect(fetchSpy).toHaveBeenCalledTimes(1)
```

**Assert Retry-After header is read and respected (JS)**
```js
vi.useFakeTimers()
server.use(
  http.get('/api/data', () => new HttpResponse(null, { status: 429, headers: { 'Retry-After': '10' } }))
)
fetchWithRetry('/api/data')
// no retry before the header interval elapses
await vi.advanceTimersByTimeAsync(9_000)
expect(fetchSpy).toHaveBeenCalledTimes(1)
await vi.advanceTimersByTimeAsync(1_100)
expect(fetchSpy).toHaveBeenCalledTimes(2)
```

**Assert HTML error page does not crash the JSON parser (Python)**
```python
@responses.activate
def test_html_error_page_does_not_crash():
    responses.add(responses.GET, 'https://api.example.com/data',
                  body='<html><body>503 Service Unavailable</body></html>',
                  content_type='text/html', status=503)
    result = api_client.fetch_data()  # should return an error object, not raise
    assert result.error is not None
    assert 'html' not in str(result.error).lower()  # no raw HTML exposed
```

**Assert 422 maps to form fields (JS)**
```js
server.use(
  http.post('/api/users', () =>
    HttpResponse.json({ errors: { email: 'already taken', age: 'must be a number' } }, { status: 422 })
  )
)
render(<CreateUserForm />)
await userEvent.click(screen.getByRole('button', { name: /submit/i }))
expect(await screen.findByText(/already taken/i)).toBeInTheDocument()
expect(await screen.findByText(/must be a number/i)).toBeInTheDocument()
expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
```

## Common gaps
- 401 and 403 handled identically — user sees "unauthorized" when they are actually logged in but forbidden
- 429 triggers an immediate retry instead of reading and waiting for the `Retry-After` value
- 204 response causes a `JSON.parse` crash on the empty body
- 422 field errors collapsed into a single generic message instead of being mapped to individual form fields
- 502/503 retried forever without backoff or a maximum attempt count
- Status 200 with `{"error": true}` in the body treated as success because only the status code is checked
- An HTML error page returned from a CDN or proxy causes the app to crash trying to parse it as JSON
- 410 Gone retried on every page load because the client does not distinguish it from a transient 404
