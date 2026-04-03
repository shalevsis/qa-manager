# Timeout Coverage Suite

## When to apply
Apply to any project that makes network requests, runs background tasks, manages sessions, or performs user-facing async operations. Detect with: grep for `fetch(`, `axios`, `requests.get`, `setTimeout`, `setInterval`, `session`, `socket`, `upload`, `download`.

## What to test

- Every outbound HTTP/API call has an explicit timeout configured — no call relies on the platform default (which is often infinite)
- Background jobs and scheduled tasks have a maximum wall-clock timeout — they cannot run forever
- WebSocket connections have a ping/pong or heartbeat timeout — dead connections are detected and reconnected
- File upload and download operations have per-operation timeouts — large files don't block indefinitely
- User session timeout: idle users are logged out after the configured period; the session is not silently extended
- Database queries have a statement timeout — runaway queries do not hold connections indefinitely
- Retry loops have a total elapsed-time cap in addition to a max-attempt count
- UI-facing operations show a timeout error to the user (not an infinite spinner) when the threshold is exceeded
- Lock acquisition timeouts: operations waiting for a mutex/lock have a timeout and handle the failure case
- Third-party SDK calls (AI APIs, payment processors) have explicit timeouts — SDK defaults are often too long

## Key patterns

**Assert HTTP call has timeout configured**
```python
def test_api_call_has_timeout(monkeypatch):
    captured = {}
    original_get = requests.get
    def mock_get(url, **kwargs):
        captured['timeout'] = kwargs.get('timeout')
        return original_get(url, **kwargs)
    monkeypatch.setattr(requests, 'get', mock_get)

    myapp.fetch_data()

    assert captured.get('timeout') is not None, "fetch_data() called requests.get without a timeout"
    assert captured['timeout'] <= 30, f"timeout too long: {captured['timeout']}s"
```

**Assert background job cannot run forever**
```python
def test_background_job_has_wall_clock_timeout():
    import signal
    def handler(signum, frame):
        raise TimeoutError("background job exceeded max duration")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(60)  # backstop: 60s max
    try:
        myapp.run_sync_job()
    finally:
        signal.alarm(0)
    # If we reach here, the job completed within 60s
```

**UI shows timeout error (not infinite spinner)**
```js
it('shows timeout error after REQUEST_TIMEOUT_MS', async () => {
  server.intercept('/api/data', req => { /* never respond */ });
  await page.click('[data-testid="load-btn"]');
  await page.waitForSelector('[data-testid="spinner"]');

  // Advance fake time past the configured timeout
  await page.evaluate(ms => { /* advance timers */ }, REQUEST_TIMEOUT_MS + 500);

  await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  await expect(page.locator('[data-testid="spinner"]')).not.toBeVisible();
  const errorText = await page.locator('[data-testid="error-message"]').textContent();
  expect(errorText).toMatch(/timed out|took too long|please try again/i);
});
```

**Session idle timeout fires**
```js
it('logs out user after idle timeout', async () => {
  vi.useFakeTimers();
  await loginAs('user@example.com');

  vi.advanceTimersByTime(SESSION_IDLE_TIMEOUT_MS);
  await nextTick();

  expect(window.location.pathname).toBe('/login');
  // or: expect(sessionStorage.getItem('token')).toBeNull();
  vi.useRealTimers();
});
```

**DB query statement timeout**
```python
def test_db_query_has_statement_timeout(db_connection):
    # Set a short statement timeout and run a query that would normally be slow
    db_connection.execute("SET statement_timeout = '5s'")
    with pytest.raises(Exception, match="statement timeout|canceling statement"):
        db_connection.execute("SELECT pg_sleep(10)")  # should be killed at 5s
```

**WebSocket heartbeat reconnects on dead connection**
```js
it('reconnects when heartbeat times out', async () => {
  vi.useFakeTimers();
  const ws = createWebSocketClient(mockServer.url);
  await ws.connect();

  // Simulate server going silent (no ping response)
  mockServer.stopResponding();
  vi.advanceTimersByTime(HEARTBEAT_TIMEOUT_MS + 1000);
  await nextTick();

  expect(ws.reconnectCount).toBe(1);
  vi.useRealTimers();
});
```

**Third-party SDK timeout explicit**
```python
def test_openai_call_has_explicit_timeout(monkeypatch):
    calls = []
    def mock_create(**kwargs):
        calls.append(kwargs)
        return MockCompletion()
    monkeypatch.setattr(openai.chat.completions, 'create', mock_create)

    myapp.run_ai_analysis("test input")

    assert calls, "AI API was not called"
    assert 'timeout' in calls[0], "AI API call missing explicit timeout"
```

## Common gaps
- `requests.get(url)` called without timeout — if the server hangs, the thread hangs forever
- Background job timeout implemented as comment: "# this should finish in under 30s" — never enforced
- Session timeout tested manually but never in automated tests — expires at wrong interval after deploy
- WebSocket heartbeat implemented but timeout value is `Infinity` in test environment config — dead connections never detected in CI
- Retry loop caps at 5 attempts but also runs for up to 10 minutes due to exponential backoff — total time cap missing
- Upload timeout set on the HTTP layer but not on the UI — spinner runs forever even after server gives up
- Third-party AI SDK has a 10-minute default timeout — acceptable in production but causes CI tests to hang on mock failures
