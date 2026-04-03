# Suite: Voice Input (Extended)

## When to apply
Use this suite for any feature that accepts speech input beyond a basic "tap and speak" smoke test. Covers edge cases in recognition quality, timing, and sequencing.

## What to test

- Short command (1–3 words) recognized correctly and the corresponding action fires
- Long prompt (30+ seconds of speech) captured fully without cutoff or truncation
- Silence or no speech: timeout fires after the configured threshold, user is notified
- Mid-speech interruption (stop button pressed): recognition stops cleanly, partial result discarded or surfaced
- Low-confidence result falls below threshold: user prompted to repeat, no action taken on bad input
- Partial interim transcript displayed while user is still speaking
- Background noise does not trigger unintended commands
- Multi-phrase sequence: each utterance processed in the correct order, no interleaving
- Utterance boundary detection: app correctly identifies when the user has stopped speaking
- Microphone permission denied: graceful error shown, no crash
- Microphone in use by another app: error shown, app does not hang

## Key patterns

```
// Short command
simulateSpeech('scan item')
expect(triggeredAction).toBe('scanItem')

// Long prompt — no cutoff
simulateSpeech(longUtterance, { durationMs: 35000 })
expect(transcript.length).toBeGreaterThanOrEqual(longUtterance.length * 0.95)

// Silence timeout
startListening()
simulateSilence({ durationMs: TIMEOUT_THRESHOLD + 500 })
expect(listeningState).toBe('idle')
expect(timeoutNotice).toBeVisible()

// Mid-speech stop
startListening()
simulateSpeech('show me the', { completeUtterance: false })
tapStopButton()
expect(listeningState).toBe('idle')
expect(noActionFired).toBe(true)

// Low-confidence threshold
mockRecognition({ transcript: 'scan item', confidence: 0.4 })
expect(retryPrompt).toBeVisible()
expect(triggeredAction).toBeNull()

// Interim transcript
startListening()
simulateInterimResult('scan i')
expect(interimDisplay).toContain('scan i')

// Background noise
simulateBackgroundNoise({ dbLevel: 'high' })
expect(commandsFired).toHaveLength(0)

// Multi-phrase ordering
simulateSpeechSequence(['command one', 'command two'])
expect(actionLog[0].command).toBe('command one')
expect(actionLog[1].command).toBe('command two')

// Utterance boundary
simulateSpeech('done speaking')
simulateSilence({ durationMs: BOUNDARY_PAUSE_MS })
expect(recognitionEndFired).toBe(true)
```

## Common gaps

- Long prompt tested with a short mock string rather than a realistic duration; actual stream cutoff not exercised
- Silence timeout not configured or set to an unreasonably long value; test passes by default
- Mid-speech stop leaves the recognition session open, causing a second result to fire later
- Low-confidence results acted on because the threshold check is missing in the action dispatcher
- Interim transcript displayed but not cleared after recognition ends, leaving stale text visible
- Background noise test skipped; noisy audio fixture not in the test asset library
- Multi-phrase sequence interleaved because async recognition callbacks are not queued
- Utterance boundary relies solely on a browser/OS event that never fires in the test environment — boundary must be explicitly simulated
- Microphone permission scenarios only tested at app launch, not mid-session
