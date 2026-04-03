# Browser/OS Permissions Suite

## When to apply
Use when the feature requests access to a device API gated by a browser permission: camera, microphone, geolocation, notifications, clipboard, or storage quota. Apply to any flow that calls `navigator.permissions` or a gated Web API.

## What to test
- Permission prompt is shown at a meaningful moment (user gesture), not on page load
- Granted permission enables the feature and the expected UI/capability appears
- Denied permission shows a graceful fallback message, not a crash or blank screen
- All prompt states handled: `not-asked`, `granted`, `denied`, `prompt`
- Permission revoked mid-session (user changes OS settings) is detected and handled
- Re-request flow after denial: UI guides user to browser/OS settings (cannot re-prompt)
- Platform differences noted: camera/mic require HTTPS on all browsers; iOS Safari has additional restrictions
- Persistent permission (granted on previous visit) skips the prompt and enables the feature immediately

## Key patterns

**Prompt triggered by user action, not mount**
```
render(<CameraFeature />)
expect(getUserMediaSpy).not.toHaveBeenCalled()
userEvent.click(startCameraButton)
expect(getUserMediaSpy).toHaveBeenCalledTimes(1)
```

**Granted — feature enabled**
```
mockPermission('camera', 'granted')
userEvent.click(startCameraButton)
await waitFor(() => expect(screen.getByTestId('video-preview')).toBeInTheDocument())
```

**Denied — graceful fallback**
```
mockPermission('camera', 'denied')
userEvent.click(startCameraButton)
expect(screen.getByText(/camera access denied/i)).toBeInTheDocument()
expect(screen.queryByTestId('video-preview')).not.toBeInTheDocument()
// No unhandled promise rejection
```

**All prompt states rendered correctly**
```
for (const state of ['prompt', 'granted', 'denied']) {
  mockPermission('geolocation', state)
  render(<LocationFeature />)
  // assert correct UI variant for each state
  cleanup()
}
```

**Revoked mid-session**
```
mockPermission('camera', 'granted')
render(<CameraFeature />)
act(() => simulatePermissionChange('camera', 'denied'))
expect(screen.getByText(/access was revoked/i)).toBeInTheDocument()
expect(stream.getTracks().every(t => t.readyState === 'ended')).toBe(true)
```

**Re-request guidance after denial**
```
mockPermission('notifications', 'denied')
userEvent.click(enableButton)
expect(screen.getByText(/open browser settings/i)).toBeInTheDocument()
// No second Notification.requestPermission() call — browser ignores it
expect(requestPermissionSpy).toHaveBeenCalledTimes(0)
```

**Persistent grant skips prompt**
```
mockPermission('geolocation', 'granted')  // already granted
render(<LocationFeature />)
await waitFor(() => expect(screen.getByTestId('map')).toBeInTheDocument())
expect(promptSpy).not.toHaveBeenCalled()
```

## Common gaps
- `denied` state only tested at component level — underlying API call still attempted and throws
- Mid-session revocation not handled — video/audio stream left open, UI shows stale "active" state
- Re-request flow missing — denial just closes a modal with no guidance to settings
- HTTPS requirement not guarded — feature attempted over HTTP, browser silently blocks with no user message
- iOS Safari differences not covered: camera constraints differ, some APIs unavailable in WKWebView
- `permissions.query` not available in all browsers — no fallback when the API itself is absent
- Permission state not persisted across page refreshes — unnecessary re-prompts on return visits
