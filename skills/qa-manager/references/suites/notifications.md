# Notifications Suite

## When to apply
Use when the feature sends browser push notifications, in-app toasts/banners, or badge counts. Apply whether notifications are triggered by user action or server push.

## What to test
- Permission prompt is shown before the first notification is sent (not on page load)
- Notification displays the correct title and body text
- Notification auto-dismisses after the expected timeout
- Notification is dismissed when the user explicitly closes it
- Badge count increments when a new notification arrives
- Badge count decrements (or clears) when notifications are read or dismissed
- Clicking a notification navigates to the correct in-app context
- No notification is shown (silent fallback) when permission is denied
- Push notification received while the app is backgrounded appears in the OS tray
- Notification not duplicated when the same event fires more than once

## Key patterns

**Permission prompt timing**
```
render(<App />)
expect(requestPermissionSpy).not.toHaveBeenCalled()   // not on mount
userEvent.click(enableNotificationsButton)
expect(requestPermissionSpy).toHaveBeenCalledTimes(1)
```

**Correct title and body**
```
act(() => triggerNotification({ title: 'New message', body: 'Alice: hey' }))
expect(NotificationConstructorSpy).toHaveBeenCalledWith(
  'New message',
  expect.objectContaining({ body: 'Alice: hey' })
)
```

**Auto-dismiss**
```
jest.useFakeTimers()
act(() => showToast('Saved'))
jest.advanceTimersByTime(5000)
expect(screen.queryByText('Saved')).not.toBeInTheDocument()
```

**Badge count increments/decrements**
```
act(() => receiveNotification())
expect(screen.getByTestId('badge')).toHaveTextContent('1')
act(() => markAllRead())
expect(screen.queryByTestId('badge')).not.toBeInTheDocument()
```

**Click navigates to correct context**
```
const notification = new Notification('New order')
act(() => notification.onclick())
expect(currentPath).toBe('/orders/99')
```

**Silent fallback when denied**
```
mockPermission('denied')
act(() => triggerNotification({ title: 'Alert' }))
expect(NotificationConstructorSpy).not.toHaveBeenCalled()
// In-app fallback may be acceptable; assert whichever is specified
```

**No duplicates**
```
act(() => {
  receiveEvent({ id: 'evt-1' })
  receiveEvent({ id: 'evt-1' })  // same event
})
expect(screen.getAllByTestId('notification-item')).toHaveLength(1)
```

## Common gaps
- Permission requested eagerly on mount — browsers may auto-block sites that do this
- Notification body not verified — only title tested
- Badge count never reaches zero — decrement logic untested
- Click handler wired to wrong route — deep-link target not verified
- Silent fallback entirely absent — denied permission throws or shows raw error
- Duplicate suppression missing — server retries cause doubled notifications
- Background push not tested because it requires a service worker — often deferred and forgotten
- Notification sound or vibration pattern tested on desktop but not mobile context
