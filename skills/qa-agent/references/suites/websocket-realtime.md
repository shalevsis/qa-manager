# WebSocket & Realtime Suite

## When to apply
Use when the feature opens a WebSocket (or SSE/long-poll) connection to push live updates to the UI. Apply to chat, live feeds, collaborative editing, and status dashboards.

## What to test
- Connection is established when the component mounts
- Incoming messages update the UI without requiring user action
- Outgoing messages are sent with the correct format/payload
- Disconnection is detected and communicated to the user (status indicator or toast)
- Automatic reconnect is attempted after disconnection, with backoff
- Duplicate messages (same ID received twice) are not rendered twice
- Message ordering is preserved (timestamp or sequence number respected)
- Component unmount closes the socket and removes all event listeners
- Offline mode queues outgoing messages and flushes them on reconnect

## Key patterns

**Connection on mount**
```
const mockSocket = { on, emit, close, off }
render(<RealtimeComponent />)
expect(mockSocket.connected).toBe(true)
```

**Incoming message updates UI**
```
act(() => mockSocket.emit('message', { id: '1', text: 'hello' }))
expect(screen.getByText('hello')).toBeInTheDocument()
```

**Outgoing message format**
```
userEvent.type(input, 'hi')
userEvent.click(sendButton)
expect(mockSocket.lastSent).toEqual({ type: 'chat', text: 'hi', roomId: '42' })
```

**Disconnection shown to user**
```
act(() => mockSocket.emit('disconnect'))
expect(screen.getByText(/disconnected/i)).toBeInTheDocument()
```

**Reconnect with backoff**
```
jest.useFakeTimers()
act(() => mockSocket.emit('disconnect'))
jest.advanceTimersByTime(1000)   // first retry
expect(connectSpy).toHaveBeenCalledTimes(2)
jest.advanceTimersByTime(2000)   // second retry (doubled)
expect(connectSpy).toHaveBeenCalledTimes(3)
```

**Duplicate suppression**
```
act(() => {
  mockSocket.emit('message', { id: '1', text: 'hello' })
  mockSocket.emit('message', { id: '1', text: 'hello' }) // duplicate
})
expect(screen.getAllByText('hello')).toHaveLength(1)
```

**Cleanup on unmount**
```
const { unmount } = render(<RealtimeComponent />)
unmount()
expect(mockSocket.close).toHaveBeenCalledTimes(1)
expect(mockSocket.off).toHaveBeenCalled()
```

**Offline queue flushed on reconnect**
```
act(() => mockSocket.emit('disconnect'))
userEvent.click(sendButton)               // queued, not sent yet
expect(mockSocket.lastSent).toBeUndefined()
act(() => mockSocket.emit('connect'))     // reconnected
expect(mockSocket.lastSent).toBeDefined()
```

## Common gaps
- `removeEventListener` / `.off()` not called on unmount — listeners accumulate across remounts
- Reconnect timer not cleared when component unmounts — attempts after destruction
- No deduplication: server retransmits on reconnect and messages double up
- Disconnection handled silently — user has no idea they are seeing stale data
- Backoff ceiling not tested — retries may escalate to very long intervals
- Outgoing messages during offline not queued, silently dropped
- Auth token not refreshed before reconnect — reconnect succeeds with expired credentials
