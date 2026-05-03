# Streaming & Server-Sent Events Suite

Detection: `EventSource`, `text/event-stream`, `ReadableStream`, chunked responses, streaming AI output, live feeds, `Transfer-Encoding: chunked`.

## When to apply
Apply when the project uses Server-Sent Events (SSE), streaming HTTP responses (e.g. streaming LLM output token-by-token), chunked transfer encoding, or any long-lived HTTP connection that delivers data progressively.

## What to test

**SSE — connection lifecycle**
- Connection opens successfully and receives initial event
- Client reconnects automatically after server closes the connection
- Client reconnects after network drop, resuming from the last received `event-id` (no duplicate events, no missed events)
- Reconnect uses exponential backoff — does not hammer the server immediately
- Connection is closed and EventSource is cleaned up when the component unmounts
- Multiple rapid reconnects do not create multiple open EventSource connections

**SSE — event handling**
- Named events (`event: update`) are routed to the correct handler
- Default message events (`event: message`) are handled separately from named events
- Malformed event data (non-JSON string when JSON expected) is caught and does not crash the handler
- Large event payloads are handled without truncation
- Events arriving in rapid succession are all processed — none dropped
- `retry:` field from server is respected — client uses the server-specified reconnect delay

**Streaming HTTP responses (ReadableStream / chunked)**
- UI renders each chunk progressively as it arrives — not buffered until stream ends
- Stream error mid-way (server drops connection) surfaces a user-facing error, not silent hang
- Stream completion (`done: true` or stream close) correctly finalizes the UI state
- Consuming a stream after it has already been consumed raises an error (streams are single-use)
- Large stream (many chunks) does not cause memory leak — chunks are processed and released

**Streaming AI output (token-by-token)**
- Each token appended to display in order — no reordering, no skipping
- Stream cancelled by user (stop button) aborts the HTTP request and clears partial output or retains it per design
- If stream is interrupted and retried, previous partial output is not duplicated
- Empty stream (zero tokens) handled — no infinite spinner, appropriate empty state shown

**Backpressure**
- Slow consumer (UI render) does not cause unbounded memory growth when producer (server) sends faster than consumed
- Stream reader properly releases lock after reading

## Key patterns

**Mock EventSource — open and receive event**
```js
// JS
const mockES = new MockEventSource('/api/stream')
mockES.dispatchEvent(new MessageEvent('message', { data: '{"token":"hello"}' }))
expect(screen.getByText('hello')).toBeInTheDocument()

# Python (sseclient)
with responses.RequestsMock() as rsps:
    rsps.add(responses.GET, '/api/stream', body='data: {"token":"hello"}\n\n',
             stream=True, content_type='text/event-stream')
    tokens = list(client.stream())
    assert tokens == [{'token': 'hello'}]
```

**EventSource cleanup on unmount**
```js
const { unmount } = render(<StreamingComponent />)
unmount()
expect(mockEventSource.close).toHaveBeenCalledTimes(1)
```

**Reconnect with exponential backoff**
```js
jest.useFakeTimers()
mockEventSource.onerror(new Event('error'))         // first drop
jest.advanceTimersByTime(1000)
expect(connectSpy).toHaveBeenCalledTimes(2)         // first retry at 1 s
mockEventSource.onerror(new Event('error'))
jest.advanceTimersByTime(2000)
expect(connectSpy).toHaveBeenCalledTimes(3)         // second retry at 2 s
```

**Resume from last-event-id**
```js
mockEventSource.dispatchEvent(new MessageEvent('message', { data: '{}', lastEventId: '42' }))
mockEventSource.onerror(new Event('error'))
jest.runAllTimers()
expect(MockEventSource.lastConstructedUrl).toContain('lastEventId=42')
// or verify the header on reconnect request
```

**Named event routed correctly**
```js
mockEventSource.addEventListener('update', handler)
mockEventSource.dispatchEvent(new MessageEvent('update', { data: '{"status":"ok"}' }))
expect(handler).toHaveBeenCalledWith(expect.objectContaining({ data: '{"status":"ok"}' }))
```

**ReadableStream — progressive render**
```js
const { readable, writable } = new TransformStream()
const writer = writable.getWriter()
render(<StreamingOutput stream={readable} />)

await writer.write(new TextEncoder().encode('Hello '))
expect(screen.getByText(/Hello/)).toBeInTheDocument()  // rendered before stream ends

await writer.write(new TextEncoder().encode('world'))
await writer.close()
expect(screen.getByText('Hello world')).toBeInTheDocument()
```

**Mid-stream disconnect surfaces error**
```js
const controller = new AbortController()
render(<StreamingOutput signal={controller.signal} />)
controller.abort()
expect(await screen.findByRole('alert')).toHaveTextContent(/connection lost/i)
```

**Stream consumed twice raises error**
```js
const stream = new ReadableStream({ start(c) { c.enqueue('data'); c.close() } })
await consumeStream(stream)
await expect(consumeStream(stream)).rejects.toThrow()
```

**Stop button aborts request**
```js
const abortSpy = jest.spyOn(AbortController.prototype, 'abort')
render(<AIOutput />)
userEvent.click(screen.getByRole('button', { name: /stop/i }))
expect(abortSpy).toHaveBeenCalledTimes(1)
```

## Common gaps
- EventSource not closed on component unmount — open connections pile up on every navigation
- Reconnect fires immediately on drop — no backoff, server gets flooded
- `last-event-id` not sent on reconnect — client re-receives events it already processed
- Named events ignored because only `onmessage` handler set, not `addEventListener('eventname')`
- Stream consumed twice — second consumer gets nothing, error swallowed
- Partial JSON across chunk boundary — parser fails because chunk split mid-JSON object
- Stop button hides UI but does not abort the HTTP stream — server keeps generating, wasting resources
