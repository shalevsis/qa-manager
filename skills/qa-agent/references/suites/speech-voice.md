# Speech & Voice Testing Reference

Mock browser APIs — real audio can't run in CI.

## What to test

**STT (SpeechRecognition):** Correct transcript processed; low-confidence fallback; no-match/silence handling; error events (network, not-allowed, audio-capture); stops after final result

**TTS (SpeechSynthesis):** `speak()` called with correct text/voice/rate; long text chunked; error handled; queue doesn't overflow

**Voice commands:** Known command → correct action; unknown command → helpful fallback; command during loading → queued or ignored

## Mocking the Web Speech API

```typescript
// vitest.setup.ts
const mockRecognition = {
  start: vi.fn(), stop: vi.fn(), abort: vi.fn(),
  onresult: null as any, onerror: null as any,
  continuous: false, interimResults: false,
}
const SpeechRecognitionMock = vi.fn(() => mockRecognition)
vi.stubGlobal('SpeechRecognition', SpeechRecognitionMock)
vi.stubGlobal('webkitSpeechRecognition', SpeechRecognitionMock)

const mockSynth = {
  speak: vi.fn(), cancel: vi.fn(), pause: vi.fn(),
  resume: vi.fn(), getVoices: vi.fn().mockReturnValue([]),
}
vi.stubGlobal('speechSynthesis', mockSynth)
```

## Simulating recognition events

```typescript
function fireResult(transcript: string, confidence = 0.9) {
  mockRecognition.onresult?.({
    results: [[{ transcript, confidence, isFinal: true }]],
    resultIndex: 0,
  })
}
function fireError(error: string) {
  mockRecognition.onerror?.({ error })
}

test('processes voice command', () => {
  render(<VoiceInterface />)
  fireEvent.click(screen.getByRole('button', { name: 'Start listening' }))
  fireResult('open settings')
  expect(screen.getByRole('dialog', { name: 'Settings' })).toBeVisible()
})
```

## Unavailable API fallback

```typescript
test('hides voice button when API unavailable', () => {
  vi.stubGlobal('SpeechRecognition', undefined)
  vi.stubGlobal('webkitSpeechRecognition', undefined)
  render(<VoiceInterface />)
  expect(screen.queryByRole('button', { name: 'Start listening' })).toBeNull()
})
```
