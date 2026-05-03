# Failure Playbook

When tests fail, use this playbook before touching anything. Classify first, act second.
Read top-to-bottom — earlier entries are more common.

---

## Classification Checklist (Phase 5)

For every failing test, determine: **is this a test bug or a production bug?**

- Test bug → you fix it (it's your file)
- Production bug → document it in QA-BACKLOG.md, mark test as "exposes known issue", stop

Never fix production code. Not even a typo. See CONSTRAINT 1.

---

## Error Patterns

### `TypeError: X is not a function` / `X.method is not a function`

**Root cause:** Test is calling the function with wrong shape, or mocking something differently than the real API.
**Diagnosis steps:**
1. Read the actual source — what does the function signature look like?
2. Read how it's exported — default vs named, class vs function?
3. Compare to how the test imports and calls it
**Fix:** Align the test import and call to match source. If the source signature changed and the test wasn't updated, that's a test bug.
**Edge case:** If the source *removed* the function entirely → production bug. Document it.

---

### `expected X, received undefined`

**Root cause:** Test is accessing a property that doesn't exist on the return value.
**Diagnosis steps:**
1. Read the source return statement — what shape does it actually return?
2. Check if the return changed in a recent commit
3. Check if you're accessing a nested property without null-guarding (`result.data.user` when `result.data` is undefined)
**Fix:** Update test assertion to match real return shape. If the property was *supposed to be there* and isn't → production bug. Document it.

---

### `expected 3, received 1` (value mismatch, not undefined)

**Root cause:** Either test assumption is wrong, or business logic is wrong.
**Diagnosis steps:**
1. Trace what the source actually computes for the test input
2. Is the expected value in the test correct? (Did you make it up or derive it from the spec?)
3. Is the source logic correct for that input?
**Decision tree:**
- Test expected value was wrong → fix the test
- Source logic has a bug → document in backlog, mark test "exposes known issue"
- Both could be right depending on spec interpretation → flag as ambiguous in report, leave test in place

---

### Test passes sometimes, fails sometimes (flaky)

**Root cause:** Non-determinism — timing, randomness, test order, or shared state.
**Diagnosis steps:**
1. Does the test involve timing (`setTimeout`, `Date.now()`, polling)?
2. Does it involve a random value or statistical computation?
3. Does it pass in isolation but fail in suite? (→ test order dependency or mock leak)
4. Does it fail only in CI but not locally? (→ timing or env difference)

**Fixes by type:**
- **Timing:** Use fake timers (`vi.useFakeTimers()`) instead of real waits
- **Statistical/random:** Widen assertion to a range (`expect(val).toBeGreaterThan(X)` not `toBeCloseTo(Y, 2)`)
- **Test order dep:** Check `afterEach` cleanup, ensure each test sets up its own state
- **Mock leak:** Add `vi.restoreAllMocks()` / `jest.resetAllMocks()` in `afterEach`
- **CI timing:** Remove real `sleep`/`wait` — use `waitFor` or mock the clock

---

### `Cannot find module './X'` / `Module not found`

**Root cause:** Wrong import path or missing dependency.
**Diagnosis steps:**
1. Does the file actually exist at that path?
2. Case sensitivity — `utils` vs `Utils` on Linux CI (case-insensitive on macOS)
3. Is it a new dependency not in `package.json`?
4. Is it a path alias (`@/components`) that needs config in the test runner?
**Fix:** Correct the import path. If it's a missing dep → note in backlog as env setup needed.

---

### `0 tests run` / suite completes with no results

**Root cause:** Test file not picked up by the test runner.
**Diagnosis steps:**
1. Check the test runner's include pattern (`testMatch`, `testPathPattern`, `testpaths`)
2. Does the filename follow the project convention? (`*.test.ts` vs `*.spec.ts` vs `__tests__/*.ts`)
3. Is the file in a directory excluded by the runner config?
**Fix:** Rename file to match convention. If convention is unclear → read existing test files in the project.

---

### All tests pass but coverage didn't increase

**Root cause:** Tests run but don't exercise the target file.
**Diagnosis steps:**
1. Is the target file imported in the test file?
2. Is the test using a mock that replaces the entire module before it runs?
3. Does the test runner include the file in its coverage scope?
**Fix:** Ensure real module is imported (not mocked). Check `coverage.include` in vitest/jest config.

---

### Test passes with wrong behavior (false positive)

**Root cause:** Assertion isn't actually checking what you think it is.
Common forms:
- `expect(fn).toHaveBeenCalled()` — fn was mocked but never called in the real path
- `expect(result).toBeTruthy()` — catches `{}`, `[]`, `"false"` as passing
- `expect(wrapper.text()).toContain('')` — empty string always passes
- Missing `await` on an async assertion
**Fix:** Make assertions specific. Replace `toBeTruthy()` with exact value checks. Add `await`. Add assertions on both the shape AND content of results.

---

### `act()` warning in React tests

**Root cause:** State update happens outside of React's render cycle during the test.
**Diagnosis steps:**
1. Is there an async state update (fetch, setTimeout) not wrapped in `act()`?
2. Are you using `@testing-library/react`? → use `waitFor` instead of manual `act`
**Fix:** Wrap async state updates in `act()`, or use `waitFor(() => expect(...))` from Testing Library. Don't suppress the warning — it indicates a real timing issue.

---

### Import/export shape mismatch (`default` vs named)

**Root cause:** Source exports as `export default X`, test imports as `import { X }` (or vice versa).
**Diagnosis steps:**
```bash
grep "^export" {source_file}
grep "^import" {test_file}
```
**Fix:** Align import style with export style.

---

## Production Bug Indicators

These failure patterns almost always mean a real bug in production code (not test code):

| Signal | Likely production bug |
|---|---|
| Test makes no assumptions about implementation, yet still fails | Business logic incorrect |
| Multiple unrelated tests all fail on same function | Function broken at root |
| Test worked before, nothing changed in test, source code changed | Regression introduced |
| Failure reproduces when you call the function directly in a REPL | Not a test setup issue |
| Error message references line in source file, not test file | Exception thrown in prod code |

When you see these: **write a clear backlog entry, mark the test "exposes known issue", stop.** Do not attempt a fix.

---

## Failure Entry Format (for QA-BACKLOG.md)

```markdown
- [ ] [QA-AGENT] BUG: {function/component} — {what it does wrong}
  - Exposed by: `{test name}` in `{test file}`
  - Symptom: {exact error or wrong output}
  - Likely cause: {one sentence if obvious, otherwise "unknown"}
  - Severity: HIGH / MEDIUM / LOW
```

---

## Lessons from Real Runs

### Luni (React/Vite/Vitest, 2026-04-02)
- Statistical tests used `toBeCloseTo(50, 1)` on weighted random → flaky → switched to `toBeGreaterThan(30) + toBeLessThan(70)`
- Stale snapshot `9→8` word count assertion failed after content change → snapshot was correct, test data was stale → updated test fixture
- Phase 5 diagnosis "test is wrong or code is wrong" wasn't actionable → added full classification checklist above
