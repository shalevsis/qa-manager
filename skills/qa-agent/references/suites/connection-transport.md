# Connection & Transport Suite

## When to apply
Apply when the project runs in production environments where network infrastructure can fail at the transport layer — below HTTP. These tests catch issues invisible in local development: DNS failures, certificate errors, connection pool exhaustion, and mid-session network type changes. Trigger this suite for production apps, mobile/hybrid apps, apps targeting multiple networks (WiFi/cellular), apps with TLS/HTTPS, DNS lookups, connection pool config, and apps running behind proxies or corporate firewalls.

## What to test

**DNS**
- DNS resolution failure (NXDOMAIN) — app shows a user-friendly "cannot reach server" error, does not crash or expose a raw stack trace
- DNS timeout — app does not hang indefinitely; a timeout fires and the user is notified
- DNS resolution succeeds after retry — transient DNS failure recovered gracefully
- Hardcoded IP addresses used as a fallback are not present in production code (brittle, bypasses DNS)

**TLS / SSL / Certificate**
- Expired certificate — app shows a clear TLS error, does not silently proceed with an insecure connection
- Self-signed certificate — rejected in production config; only accepted in test environments with an explicit override
- Certificate hostname mismatch — connection rejected, not silently allowed
- TLS version too old (TLS 1.0/1.1) — server rejects or app enforces minimum TLS 1.2
- Mixed content (HTTPS page loading HTTP resource) — blocked by browser; no silent downgrade
- Certificate pinning (mobile): pinned cert mismatch is detected and connection refused
- HSTS (HTTP Strict Transport Security) header present on all HTTPS responses

**Connection pooling**
- Pool exhaustion: when all connections are in use, new requests queue or fail fast with an error rather than hanging indefinitely
- Connections are returned to the pool after request completion — no connection leak
- Idle connection timeout: stale connections removed from pool before the server-side timeout closes them, avoiding "connection reset" errors
- Pool size configured appropriately for expected concurrency — not defaulted to 1 or unlimited

**Network type changes**
- WiFi → cellular switch mid-session: in-flight requests are retried or completed cleanly, app does not freeze
- Cellular → WiFi: app detects improved connectivity and does not continue using degraded settings
- Flight mode enabled mid-session: app enters offline state cleanly without crashing
- Network type detected and used to adjust quality settings (e.g. lower image resolution on cellular)

**Proxy and firewall**
- App works correctly behind a corporate HTTP/HTTPS proxy
- Proxy authentication (407 Proxy Authentication Required) handled — user is prompted or credentials from config are used
- Requests blocked by a firewall produce a user-visible error, not a silent hang
- `CONNECT` tunnel for HTTPS through a proxy is established correctly

**IPv4 / IPv6**
- App works on an IPv6-only network (Happy Eyeballs / dual-stack fallback)
- IPv6 address literals in URLs are formatted correctly (`[::1]`, not `::1`)
- No hardcoded IPv4 assumptions in network code

**Connection reset / abrupt closure**
- `ECONNRESET` — server closes connection mid-response; app retries or shows a user-facing error
- `ECONNREFUSED` — server not running; app shows "service unavailable", not an unhandled exception
- `ETIMEDOUT` — connection establishment timed out; distinct user message from a request-level timeout

## Key patterns

**DNS failure (Node.js / nock)**
```js
import nock from 'nock'

nock.disableNetConnect()
nock('https://api.example.com')
  .get('/data')
  .replyWithError({ code: 'ENOTFOUND', message: 'getaddrinfo ENOTFOUND api.example.com' })

await expect(fetchData()).rejects.toThrow()
expect(userErrorMessage).toMatch(/cannot reach server|check your connection/i)
// must not be an unhandled rejection or raw ENOTFOUND trace
```

**DNS failure (Python / pytest-httpx)**
```python
import httpx, pytest

def test_dns_failure_shows_friendly_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("ENOTFOUND"))
    with pytest.raises(AppError) as exc_info:
        fetch_data()
    assert "cannot reach server" in str(exc_info.value).lower()
```

**TLS certificate error (Playwright)**
```js
// Playwright surfaces cert errors via page.on('pageerror') or request failure
const errors = []
page.on('requestfailed', req => errors.push(req.failure().errorText))

await page.goto('https://expired.badssl.com/')
expect(errors.some(e => /cert|tls|ssl/i.test(e))).toBe(true)
// App-level: assert an error UI is shown, not a blank page
await expect(page.locator('[data-testid="tls-error-banner"]')).toBeVisible()
```

**TLS error (Python)**
```python
import httpx, pytest

def test_expired_cert_raises_not_swallowed(httpx_mock):
    httpx_mock.add_exception(httpx.RemoteProtocolError("SSL: CERTIFICATE_VERIFY_FAILED"))
    with pytest.raises(AppTLSError):
        fetch_secure_resource()
    # must not silently return empty data
```

**Connection pool exhaustion (Node.js)**
```js
// Fire more concurrent requests than the pool allows; assert queuing / fast-fail
const MAX_POOL = 5
const requests = Array.from({ length: MAX_POOL + 3 }, () => client.get('/api/item'))
const results = await Promise.allSettled(requests)
const failed = results.filter(r => r.status === 'rejected')
// Either all succeed (queued) or extras fail with a clear error — no indefinite hang
expect(failed.every(f => f.reason.message)).toBe(true)
```

**Connection pool exhaustion (Python / SQLAlchemy example)**
```python
from sqlalchemy.exc import TimeoutError as PoolTimeout

def test_pool_exhaustion_raises_not_hangs():
    # pool_size=2, max_overflow=0, pool_timeout=1
    engine = create_engine(DB_URL, pool_size=2, max_overflow=0, pool_timeout=1)
    conns = [engine.connect() for _ in range(2)]
    with pytest.raises(PoolTimeout):
        engine.connect()   # third connection must fail fast, not hang
    for c in conns:
        c.close()
```

**Connection leak — pool returns connection after exception (Node.js)**
```js
server.intercept('/api/fail', req => req.reply(500))
try { await client.get('/api/fail') } catch {}
// Verify the connection was returned: subsequent requests should succeed without timeout
await expect(client.get('/api/ok')).resolves.toMatchObject({ status: 200 })
```

**AbortController connect timeout (JS)**
```js
import nock from 'nock'

nock('https://api.example.com').get('/slow').delay(5000).reply(200)

const controller = new AbortController()
const timer = setTimeout(() => controller.abort(), 1000)

await expect(
  fetch('https://api.example.com/slow', { signal: controller.signal })
).rejects.toThrow(/aborted|timed out/i)
clearTimeout(timer)
```

**AbortController connect timeout (Python)**
```python
import httpx, pytest

def test_connect_timeout_raises(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectTimeout("timed out"))
    with pytest.raises(httpx.ConnectTimeout):
        httpx.get("https://api.example.com/slow", timeout=1.0)
```

**ECONNRESET / ECONNREFUSED (Node.js)**
```js
nock('https://api.example.com')
  .get('/resource')
  .replyWithError({ code: 'ECONNRESET' })

const result = await fetchWithRetry('/resource')
// Should retry; if retries exhausted, surface a clean error
expect(result.error).toMatch(/service unavailable|connection lost/i)
```

**ECONNRESET / ECONNREFUSED (Python)**
```python
def test_econnrefused_shows_service_unavailable(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("ECONNREFUSED"))
    response = app_client.get("/proxy-endpoint")
    assert response.status_code == 503
    assert "service unavailable" in response.json()["error"].lower()
```

**IPv6 address literal formatting**
```js
// Ensure URL construction wraps IPv6 literals correctly
const addr = '::1'
const url = buildUrl(addr, 8080, '/api')
expect(url).toBe('http://[::1]:8080/api')   // not 'http://::1:8080/api'
```

**HSTS header presence (Python)**
```python
def test_hsts_header_present(client):
    resp = client.get("/")
    assert "strict-transport-security" in resp.headers
    assert "max-age=" in resp.headers["strict-transport-security"]
```

## Common gaps
- DNS failure causes an unhandled exception — raw stack trace shown to user instead of a friendly message
- `NODE_TLS_REJECT_UNAUTHORIZED=0` left in the production environment — self-signed certs silently accepted
- Connection pool defaults to unlimited — under load, DB or API connections are exhausted without warning
- Connections not returned to the pool when a request throws an exception — pool slowly depletes until the app stalls
- WiFi → cellular transition causes an in-flight WebSocket to drop permanently with no reconnect attempted
- A single hardcoded `http://` URL in one config file prevents HTTPS enforcement across the app
- `ECONNRESET` is logged but not retried — user sees an empty page because the one failed request was critical
- IPv6 never tested — app breaks on networks that only route IPv6 (increasingly common on mobile)
- Connect timeout and request timeout treated identically — user sees the wrong error message, obscuring the root cause
- Proxy `407` response not handled — app hangs or crashes behind corporate firewalls instead of prompting for credentials
