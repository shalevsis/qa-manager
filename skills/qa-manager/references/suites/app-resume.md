# App Resume Suite

## When to apply
Apply when testing mobile apps, PWAs, or any browser-based app where users may background the app, lock their device, or switch tabs and return after an indeterminate period. Covers both short suspensions (seconds) and long ones (hours, where tokens may expire).

## What to test

- App backgrounded then foregrounded: form input values and scroll position are preserved
- Device sleep or screen lock then wake: session is still valid, or the user is prompted to re-authenticate gracefully
- Browser tab hidden then made visible again: polling and timers that should pause actually did pause; they resume on visibility
- `setInterval` behavior while backgrounded: interval is paused or rate-capped; no burst of accumulated calls on resume
- Unsaved form input: not lost when the user switches apps and returns, even if the OS kills the background tab
- Auth token expiry during sleep: re-authentication is smooth; raw 401 responses are never surfaced to the user
- Network reconnect after sleep: app detects the reconnect event and refreshes or resumes correctly
- Stale data after long background: a staleness indicator or timestamp is shown and a refresh is offered

## Key patterns

**UI state preserved after background/foreground**
```
fillForm({ name: 'Test User', email: 'test@example.com' })
simulateBackground()
simulateForeground()
expect(formField('name').value).toBe('Test User')
expect(formField('email').value).toBe('test@example.com')
expect(scrollPosition()).toBe(savedPosition)
```

**Graceful re-auth after token expiry**
```
setTokenExpiry(Date.now() - 1000)   // already expired
simulateSleep(3600_000)             // 1-hour sleep
simulateWake()
// Should not flash a 401 error — should redirect to login or silently refresh
expect(rawErrorMessage('401')).not.toBeVisible()
expect(loginPrompt or refreshedSession).toBeTruthy()
```

**Timers pause on hidden tab**
```
const calls = []
startPolling(() => calls.push(Date.now()), 1000)

setTabVisibility('hidden')
advanceTimersByMs(10_000)
const countWhileHidden = calls.length

setTabVisibility('visible')
advanceTimersByMs(1_000)

expect(countWhileHidden).toBe(0)   // or <= 1 if one immediate tick allowed
expect(calls.length).toBe(1)       // resumed after visible
```

**`setInterval` burst prevention**
```
// Simulate browser throttling: tab hidden for 30 s, then shown
document.dispatchEvent(new Event('visibilitychange'))   // hidden
vi.advanceTimersByTime(30_000)
document.dispatchEvent(new Event('visibilitychange'))   // visible
// Interval should not fire 30 queued ticks at once
expect(intervalCallCount).toBeLessThanOrEqual(2)
```

**Unsaved input survives app switch**
```
fillForm({ draft: 'Important note' })
simulateAppSwitch()    // OS may kill tab; check sessionStorage/localStorage
simulateReturn()
expect(formField('draft').value).toBe('Important note')
// or confirm draft was persisted to storage:
expect(sessionStorage.getItem('form_draft')).toContain('Important note')
```

**Network reconnect after sleep**
```
goOffline()
advanceTimersByMs(60_000)
goOnline()
await waitForReconnectHandler()
const requests = capturedRequests('/api/feed')
expect(requests.length).toBe(1)               // one refresh, not a burst
expect(displayedData).toBeRecent()
expect(staleDataBanner).not.toBeVisible()
```

**Stale data indicator after long background**
```
setLastFetchedAt(Date.now() - STALE_THRESHOLD_MS - 1000)
simulateForeground()
expect(staleBanner or timestampLabel).toBeVisible()
expect(refreshButton).toBeEnabled()
```

## Common gaps

- Testing only that state persists in memory — not that it survives an OS-level tab kill (check localStorage/sessionStorage)
- Not testing the `visibilitychange` event directly; instead relying on manual tab switching, which is non-deterministic in CI
- Forgetting that token refresh on wake may itself fail (e.g. refresh token also expired) — test that failure path too
- Assuming `setInterval` is always throttled by the browser — behavior varies; test with fake timers, not wall-clock sleep
- Not verifying that WebSocket or SSE connections are re-established after wake, not just HTTP polling
- Skipping the scenario where the user returns to the app mid-form after a long absence and submits stale CSRF tokens
- Not asserting that a burst of queued interval ticks does not trigger duplicate API mutations on resume
