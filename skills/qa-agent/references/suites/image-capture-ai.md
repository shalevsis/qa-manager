# Suite: Image Capture + AI Analysis (Baseline Happy Path)

## When to apply
Use this suite as the baseline for any feature that captures or uploads an image and feeds it to an AI model for analysis. Run it before any specialized camera, upload, or AI robustness suites.

## What to test

- Permission prompt appears on first launch of the capture feature
- Granting permission allows the camera/file picker to open
- Denying permission shows the correct error message and no camera UI
- Capture or file selection completes and image is previewed
- Upload initiates immediately (or on explicit confirm) with a visible loading state
- Upload completion triggers AI analysis with its own loading state
- AI analysis result is displayed correctly in the UI
- Each stage writes a log entry: start capture, upload complete, analysis complete, error
- Retry button appears after analysis failure and re-triggers the full analysis step
- UI is blocked from re-capturing (button disabled or hidden) during active analysis
- Network failure during upload shows a specific network error (not a generic crash)
- Analysis failure shows a specific analysis error (not a network error)
- Permission denial shows a permission-specific error (not a generic error)
- End-to-end flow completes without console errors or unhandled promise rejections

## Key patterns

```
// Assert loading state is present during upload
expect(uploadLoadingIndicator).toBeVisible()
// Assert loading state is present during analysis
expect(analysisLoadingIndicator).toBeVisible()

// Assert correct log entries in order
expect(log).toContain({ event: 'capture_start' })
expect(log).toContain({ event: 'upload_complete' })
expect(log).toContain({ event: 'analysis_complete' })

// Assert UI is blocked during analysis
expect(captureButton).toBeDisabled()

// Assert retry button present after analysis error
mockAnalysisAPI({ status: 500 })
triggerCapture()
expect(retryButton).toBeVisible()

// Assert correct error type per failure mode
mockPermission('denied')
expect(errorMessage).toMatch(/permission/i)

mockNetwork({ offline: true })
expect(errorMessage).toMatch(/network/i)

mockAnalysisAPI({ status: 500 })
expect(errorMessage).toMatch(/analysis/i)
```

## Common gaps

- Loading state for upload and analysis tested as one combined spinner — they should be separate, observable states
- Log entries verified only on success, not on each error path
- Retry button re-triggers the entire flow (re-capture) instead of just the analysis step
- UI block only checked visually; the underlying action handler still fires on rapid taps
- Error messages are generic ("Something went wrong") across all three failure modes — each must be distinct
- Permission denial path not tested after the first session (requires resetting permission state between runs)
- Log entries written with wrong stage label (e.g., "upload_complete" fired before server confirms receipt)
