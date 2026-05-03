# Suite: Regression Traps

## When to apply
Apply when the codebase has constants that, if changed accidentally, would silently break user-facing behavior — storage keys that would wipe saved data, scoring values that would alter user progress, thresholds that gate feature logic.

---

## What to test

- Storage/persistence keys have not changed (a rename wipes all user data)
- Scoring and XP constants match the values the rest of the logic was built around
- Star/badge/unlock thresholds remain at their calibrated values
- Version identifiers used for migration logic are stable
- Feature flags default to their intended values
- Critical string literals used in routing, analytics, or external integrations are unchanged

---

## Key patterns

**The trip-wire pattern — the comment IS the documentation:**
```js
// REGRESSION TRAP: If STORAGE_KEY ever changes, all users lose their saved progress.
// This test exists to make that change loud and deliberate, not accidental.
it('STORAGE_KEY has the expected value', () => {
  expect(STORAGE_KEY).toBe('expected_key_string');
});

// REGRESSION TRAP: XP_PER_CORRECT is load-bearing — leaderboard rankings, streak
// logic, and level-up thresholds all depend on this exact value. Any change
// must be intentional and accompanied by a migration or recalibration.
it('XP_PER_CORRECT has the expected value', () => {
  expect(XP_PER_CORRECT).toBe(EXPECTED_XP_VALUE);
});

// REGRESSION TRAP: STAR_THRESHOLD controls when a user earns a star. Lowering it
// inflates progress; raising it silently demotes users who already earned stars.
it('STAR_THRESHOLD has the expected value', () => {
  expect(STAR_THRESHOLD).toBe(EXPECTED_THRESHOLD);
});

// REGRESSION TRAP: APP_VERSION is read during startup to trigger data migrations.
// Bumping it incorrectly can re-run migrations on existing users or skip them for new ones.
it('APP_VERSION has the expected value', () => {
  expect(APP_VERSION).toBe('EXPECTED_VERSION_STRING');
});
```

**Feature flag defaults:**
```js
// REGRESSION TRAP: This flag defaults to false in production. A change to true
// would enable an incomplete feature for all users without a rollout.
it('FEATURE_FLAG_X defaults to false', () => {
  expect(FEATURE_FLAG_X).toBe(false);
});
```

**Batch-check a group of constants:**
```js
it('critical constants match their calibrated values', () => {
  const snapshot = {
    STORAGE_KEY: 'expected_key',
    XP_PER_CORRECT: EXPECTED_XP,
    MAX_STREAK_BONUS: EXPECTED_BONUS,
    BADGE_UNLOCK_THRESHOLD: EXPECTED_BADGE_THRESHOLD,
  };
  Object.entries(snapshot).forEach(([name, expected]) => {
    expect({ [name]: eval(name) }).toEqual({ [name]: expected });
  });
});
```

---

## Common gaps

- Not writing these tests because they feel "too trivial" — that is precisely the point
- Testing that a constant is defined (`toBeDefined`) but not asserting its exact value
- Covering scoring constants but forgetting storage keys — the most dangerous category
- No tests for version strings used in migration guards
- Feature flags tested for existence but not for their production default value
- Constants duplicated across files — only one copy is tested, the other drifts silently
- Skipping the explanatory comment — without it, a future developer deletes the "pointless" test
