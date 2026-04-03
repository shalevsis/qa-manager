# Suite: Camera Hardware Edge Cases

## When to apply
Use this suite when the feature uses a native camera stream (not file-picker only). Run after the baseline image-capture-ai suite passes.

## What to test

- Front and back camera switch updates the live preview without freezing
- Torch/flash toggles on and off; state reflected in UI icon
- Camera permission revoked mid-session (OS settings change while app is open): app detects loss and prompts re-request or shows graceful fallback
- Camera in use by another app: error shown, app does not crash or hang
- Device has no camera hardware: camera option hidden, file upload fallback offered
- Portrait-to-landscape rotation during capture: preview redraws to correct aspect ratio
- Landscape-to-portrait rotation during capture: same as above
- Low-memory condition during stream: stream degrades or terminates gracefully, error shown
- Navigating away from camera view stops the stream (no resource leak)
- Returning to camera view after navigation restarts the stream cleanly

## Key patterns

```
// Camera switch
tapCameraSwitch()
expect(activeCamera).toBe('front') // was 'back'
expect(preview).toBeVisible()
expect(preview).not.toBeFrozen()

// Torch toggle
tapTorchButton()
expect(torchIcon).toShowState('on')
tapTorchButton()
expect(torchIcon).toShowState('off')

// Permission revoked mid-session
grantCameraPermission()
openCameraView()
revokePermission('camera') // simulate OS revoke
expect(permissionPromptOrFallback).toBeVisible()
expect(app).not.toCrash()

// Camera busy
simulateCameraBusyByOS()
openCameraView()
expect(errorMessage).toMatch(/camera.*unavailable|in use/i)

// No hardware
simulateNoCameraHardware()
expect(cameraButton).not.toBeVisible()
expect(fileUploadButton).toBeVisible()

// Orientation
rotateDevice('landscape')
expect(previewAspectRatio).toMatch('landscape')

// Navigation leak check
openCameraView()
navigateAway()
expect(cameraStream).toBeStopped()
```

## Common gaps

- Camera switch tested only from back-to-front, not front-to-back
- Torch state not reset when camera is closed and reopened (persists incorrectly)
- Permission revocation tested only at app launch, not mid-session
- "Camera busy" scenario skipped entirely because it is hard to simulate — use a mock/stub
- No-hardware path only hides the button but still attempts to initialize the camera in code
- Orientation change tested visually but preview aspect ratio not asserted programmatically
- Stream leak: navigating away stops the UI but `getUserMedia` track is not explicitly stopped
- Low-memory path never tested; stream failure leaves a spinner running indefinitely
