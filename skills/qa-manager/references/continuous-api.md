# Continuous External API Testing Reference

## What to test

- **Polling:** Starts, ticks at right interval, stops on completion/error/unmount
- **Retry:** Retries after failure with exponential backoff; stops at maxRetries
- **Rate limiting (429):** Backs off using Retry-After header
- **Cleanup:** Polling stops on component unmount (no memory leaks)
- **Deduplication:** No new request if one is already in flight

## Fake timers + fetch mock

```typescript
beforeEach(() => {
  vi.useFakeTimers()
  vi.spyOn(global, 'fetch')
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

test('polls every 5 seconds', async () => {
  fetch.mockResolvedValue(new Response(JSON.stringify({ status: 'pending' })))
  startPolling('/api/job/123', { interval: 5000 })
  expect(fetch).toHaveBeenCalledTimes(1)
  await vi.advanceTimersByTimeAsync(5000)
  expect(fetch).toHaveBeenCalledTimes(2)
})

test('stops polling on unmount', async () => {
  fetch.mockResolvedValue(new Response(JSON.stringify({ status: 'running' })))
  const { unmount } = render(<JobStatus jobId="123" interval={5000} />)
  await vi.advanceTimersByTimeAsync(5000)
  unmount()
  const countAtUnmount = fetch.mock.calls.length
  await vi.advanceTimersByTimeAsync(10000)
  expect(fetch).toHaveBeenCalledTimes(countAtUnmount)  // no more calls
})
```

## Retry with backoff

```typescript
test('retries with exponential backoff', async () => {
  fetch.mockRejectedValueOnce(new Error('fail')).mockRejectedValueOnce(new Error('fail')).mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })))
  const result = fetchWithRetry('/api/data', { maxRetries: 3, baseDelay: 1000 })
  await vi.advanceTimersByTimeAsync(1000)
  await vi.advanceTimersByTimeAsync(2000)
  await expect(result).resolves.toEqual({ ok: true })
})
```

## Rate limit (429)

```typescript
test('backs off on 429', async () => {
  fetch
    .mockResolvedValueOnce(new Response(null, { status: 429, headers: { 'Retry-After': '30' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ data: 'ok' })))
  const result = fetchWithRateLimit('/api/data')
  await vi.advanceTimersByTimeAsync(30000)
  await expect(result).resolves.toEqual({ data: 'ok' })
})
```
