# Suite: AI Vision Robustness

## When to apply
Use this suite when the app passes images to an AI vision model and displays or acts on the results. Run after the baseline image-capture-ai suite passes.

## What to test

- Empty scene or non-target subject returns a graceful "couldn't identify" message, not a crash
- Multiple subjects in frame: app handles an array response or selects the primary subject deterministically
- Ambiguous or similar-looking subjects: confidence score displayed or a minimum threshold applied before acting
- Completely unknown subject: fallback UI shown, no crash or unhandled error
- Partially visible or obscured subject: handled without error; result may be low-confidence
- Same image submitted twice: result is consistent, or expected variance is documented and tested
- AI model version update: results snapshot-tested or version-pinned to prevent silent regressions
- Null response body from AI: error shown, no null-reference crash
- Empty array or empty string in response: treated as "no result found", not as a valid result
- Malformed JSON response: parse error caught, user-facing error shown
- HTTP 429 (rate limited): retry with exponential backoff, user informed of delay
- AI cost per call logged or tracked for budget monitoring

## Key patterns

```
// No target found
mockAI({ result: [] })
submitImage(emptySceneFixture)
expect(noResultMessage).toBeVisible()
expect(app).not.toCrash()

// Multiple subjects
mockAI({ result: [subjectA, subjectB] })
submitImage(multiSubjectFixture)
expect(displayedResult).toBe(subjectA) // primary selected

// Confidence threshold
mockAI({ result: [{ label: 'item', confidence: 0.3 }] })
submitImage(ambiguousFixture)
expect(lowConfidenceWarning).toBeVisible() // or result withheld

// Unknown subject
mockAI({ result: [{ label: 'unknown' }] })
expect(fallbackUI).toBeVisible()

// Null response
mockAI({ body: null })
expect(errorMessage).toBeVisible()
expect(app).not.toCrash()

// Malformed JSON
mockAI({ rawBody: '<!DOCTYPE html>' })
expect(parseErrorMessage).toBeVisible()

// Rate limiting with backoff
mockAI({ status: 429, retryAfter: 2 })
expect(retryAttempts).toBeGreaterThan(0)
expect(retryDelays).toBeExponential()
expect(userFacingDelay).toBeVisible()

// Cost tracking
submitImage(fixture)
expect(costLog).toContain({ event: 'ai_call', tokens: expect.any(Number) })
```

## Common gaps

- Empty array response `[]` treated the same as a successful result with no items — no "not found" message shown
- Multiple subjects: first array element displayed without any deterministic ordering; result changes between calls
- Confidence score received but never shown to the user or used as a gate
- Null response body causes a null-reference exception that bubbles as an unhandled rejection
- Malformed JSON (e.g., HTML error page from a proxy) crashes the JSON parser with no catch block
- 429 handling retries immediately in a tight loop instead of backing off, worsening rate limiting
- Model version update silently changes results; no snapshot test or version assertion in place
- AI cost never logged; runaway usage not detectable until the billing cycle
