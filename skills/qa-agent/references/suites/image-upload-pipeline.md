# Suite: Image Upload Pipeline

## When to apply
Use this suite for any feature that uploads image data to a remote server. Focus on transfer reliability, progress accuracy, and concurrency safety.

## What to test

- Progress bar reflects actual bytes transferred, not a fake timed animation
- Network drop mid-upload shows a specific error and presents a retry option
- Network type switch (WiFi to cellular) mid-upload does not silently fail or hang
- Offline queue: upload initiated offline is stored and retried automatically on reconnect
- Concurrent uploads from rapid successive captures do not corrupt each other or the server state
- Duplicate image uploaded twice is deduplicated (same file not stored or processed twice)
- Upload initiated in a background tab completes, pauses gracefully, or resumes when foregrounded
- Upload cancelled by the user stops the transfer and cleans up any partial server state
- Server returns 4xx: error shown, no retry (user action required)
- Server returns 5xx: error shown, retry offered

## Key patterns

```
// Progress accuracy
interceptUpload({ trackBytes: true })
startUpload(imageFixture)
expect(progressBar.value).toApproximatelyEqual(bytesTransferred / totalBytes)

// Mid-upload network drop
startUpload(imageFixture)
simulateNetworkDrop({ afterPercent: 50 })
expect(errorMessage).toBeVisible()
expect(retryButton).toBeVisible()

// WiFi to cellular handoff
startUpload(largeImageFixture)
switchNetworkType('cellular')
expect(upload).toCompleteOrShowError() // must not silently hang

// Offline queue
goOffline()
triggerUpload(imageFixture)
expect(pendingQueue).toHaveLength(1)
goOnline()
expect(pendingQueue).toHaveLength(0)
expect(serverReceivedUploads).toHaveLength(1)

// Concurrent uploads
rapidlyCapture(3)
await allUploadsComplete()
expect(serverReceivedUploads).toHaveLength(3)
expect(serverReceivedUploads.map(u => u.data)).allToBeDistinct()

// Deduplication
uploadSameFile(imageFixture, imageFixture)
expect(serverReceivedUploads.deduplicated).toHaveLength(1)

// 4xx vs 5xx handling
mockServer({ status: 400 })
expect(retryButton).not.toBeVisible()

mockServer({ status: 500 })
expect(retryButton).toBeVisible()
```

## Common gaps

- Progress bar driven by a `setInterval` animation instead of `XMLHttpRequest.upload.onprogress` or equivalent
- Network drop mid-upload leaves the UI in a loading state indefinitely (no timeout or error handler)
- WiFi-to-cellular switch silently resets the connection; app treats it as a completed upload
- Offline queue fires multiple retries simultaneously on reconnect, causing duplicate server entries
- Concurrent upload IDs collide due to timestamp-based ID generation within the same millisecond
- Deduplication based on filename only; same content with different name uploaded twice
- Background tab upload: `fetch` completes but result callback is never processed after refocus
- Partial server state (half-written file) not cleaned up after a cancelled or failed upload
