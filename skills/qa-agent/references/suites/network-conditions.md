# Network Conditions Suite

## When to apply
Apply when testing any feature that makes network requests, shows loading states, or needs to handle unreliable connectivity. Use Playwright's `page.route` to throttle or abort requests; test retry and timeout logic directly in unit tests.

## What to test

- Slow 3G conditions: loading indicators appear and the app does not crash or time out prematurely
- High-latency responses (1–3 s): UI shows a spinner or skeleton; does not appear frozen or unresponsive
- Intermittent failures (simulate 1-in-3 requests failing): retry logic fires automatically, user is notified after retries are exhausted
- Complete offline state: app enters a clear offline mode, queues any user actions, and does not crash
- Timeout threshold: requests are abandoned after the configured limit and show a user-facing error (not an infinite wait)
- Large payload on a slow connection: progress indication is shown and the user can cancel mid-transfer
- Network recovery after disconnect: app resumes with fresh data; no stale cache served silently; no duplicate requests fired
- Connection type change mid-flight (e.g. WiFi to cellular): in-flight requests are handled gracefully, not silently dropped

## Key patterns

**Slow 3G throttle (Playwright)**
```
await page.route('**/*', async route => {
  await new Promise(r => setTimeout(r, 500))   // add per-request latency
  await route.continue()
})
// Assert loading indicator is visible before response arrives
await expect(page.locator('[data-testid="spinner"]')).toBeVisible()
```

**High latency — spinner shown**
```
mockServer.delay('/api/data', 2000)
triggerDataFetch()
expect(spinner).toBeVisible()          // visible during wait
await settle()
expect(spinner).not.toBeVisible()      // hidden after response
```

**Intermittent failures with retry**
```
let callCount = 0
server.intercept('/api/resource', req => {
  callCount++
  if (callCount % 3 !== 0) req.reply(500)
  else req.passThrough()
})
await triggerAction()
expect(callCount).toBeGreaterThan(1)           // retry fired
expect(userNotification).not.toBeVisible()     // recovered silently
// exhaust retries:
server.intercept('/api/resource', req => req.reply(500))
await triggerAction()
expect(userNotification).toBeVisible()         // error shown after retries
```

**Complete offline**
```
await context.setOffline(true)
triggerAction()
expect(offlineBanner).toBeVisible()
expect(page).not.toHaveURL(/error/)   // no crash/redirect
// queued action replays on reconnect:
await context.setOffline(false)
await settle()
expect(actionCompleted).toBe(true)
```

**Timeout threshold**
```
server.intercept('/api/slow', req => { /* never respond */ })
triggerRequest()
await advanceTimersByMs(REQUEST_TIMEOUT_MS + 100)
expect(errorMessage).toBeVisible()
expect(errorMessage.text).toMatch(/timed out|took too long/i)
```

**Large payload with cancel**
```
mockSlowStream('/api/download', { bytesPerSecond: 50_000 })
startDownload()
expect(progressBar).toBeVisible()
clickCancel()
expect(downloadAborted).toBe(true)
expect(progressBar).not.toBeVisible()
```

**Recovery — no stale data, no duplicate requests**
```
await context.setOffline(true)
await context.setOffline(false)
const requests = captureRequests('/api/feed')
await waitForRecovery()
expect(requests.length).toBe(1)           // exactly one refresh, not duplicated
expect(displayedData.timestamp).toBeRecent()
```

## Common gaps

- Testing only that loading states appear, not that they disappear correctly after recovery
- Not asserting the exact retry count or back-off interval — retry logic may fire but with wrong delay
- Forgetting to test what happens when the user interacts (e.g. submits a form) during a retry window
- Assuming `navigator.onLine` is a reliable offline signal — it is not; test with actual network interception
- Not canceling pending requests when the component unmounts, leading to state updates on unmounted components
- Skipping the "recovery after long offline" scenario where auth tokens may have expired during the outage
- Not verifying that the request queue drains in order and without duplicates after reconnection
