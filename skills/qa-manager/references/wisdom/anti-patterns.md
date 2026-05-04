# QA Anti-Patterns

Cross-project testing mistakes collected from real runs. Read this before writing tests (Phase 3).
Each pattern: what it looks like, why it fails, what to do instead.

---

## Suite Selection Anti-Patterns

### Selecting suites without checking env capabilities
**Looks like:** Loading `camera-hardware.md` or `speech-voice.md` in a Jest/Vitest env with no jsdom mock.
**Fails:** Tests written that can never pass — `getUserMedia`, `SpeechRecognition` don't exist in Node.
**Do instead:** Phase 1 Step A first. If env lacks support, still write the tests but mark LOW confidence with a "requires: [env setup]" note.

### Selecting every suite by keyword match
**Looks like:** Project has a `login.js` → loads `auth-session.md` + `application-security.md` + `permissions.md` + `tls-certificates.md` all at HIGH.
**Fails:** Token inflation, redundant tests, misleading confidence tiers.
**Do instead:** Stack-rank by signal strength. A single `jwt.verify()` call does not warrant 4 auth suites.

---

## Test Writing Anti-Patterns

### Testing the mock, not the behavior
**Looks like:**
```js
vi.mock('./api')
api.getUser.mockResolvedValue({ id: 1 })
expect(api.getUser).toHaveBeenCalled() // ← testing the mock
```
**Fails:** The real `getUser` could be broken and this test always passes.
**Do instead:** Mock only at system boundaries (network, filesystem, time, browser APIs). Test the component/function that USES `getUser`, not `getUser` itself. Assert on output behavior.

### Over-mocking internal collaborators
**Looks like:** Mocking a helper function that lives in the same module as the code under test.
**Fails:** You're now testing an isolated shell with all logic removed. Refactors don't break these tests — but neither do real bugs.
**Do instead:** Only mock what crosses a system boundary. Internal functions get tested through the public interface.

### Testing implementation instead of contract
**Looks like:** Test breaks when you rename a private variable or extract a helper function.
**Fails:** Tests are tightly coupled to code structure. Every refactor requires test rewrites.
**Do instead:** Test inputs → outputs. What does the function return given X? What side effect happens given Y? Not how it achieves it internally.

### Missing negative / error path tests
**Looks like:** 5 happy path tests, 0 error cases.
**Fails:** Error handling goes untested. Null inputs, network failures, malformed data all unvalidated.
**Do instead:** For every function, ask: what happens with null? empty string? negative number? what if the async call rejects? Test those paths.

### Snapshot tests as a substitute for assertions
**Looks like:** `expect(component).toMatchSnapshot()` on every render test.
**Fails:** Snapshots silently become stale. A UI regression that "looks wrong" still passes if the snapshot was already wrong. Reviewers rubber-stamp snapshot diffs.
**Do instead:** Snapshot sparingly. Prefer explicit assertions on specific output values (`expect(heading.textContent).toBe('...')`).

### Asserting too broadly with `toMatchObject`
**Looks like:** `expect(result).toMatchObject({ status: 'ok' })` — ignores everything else.
**Fails:** Extra unwanted properties go unchecked. API drift not caught.
**Do instead:** When shape matters, use `toStrictEqual`. Reserve `toMatchObject` for when partial matching is intentional.

---

## Async Anti-Patterns

### Forgetting to await
**Looks like:**
```js
it('saves user', () => {          // ← missing async
  saveUser({ name: 'Alice' })    // ← missing await
  expect(db.users).toHaveLength(1) // runs before save completes
})
```
**Fails:** Test always passes — the assertion runs before the promise resolves.
**Do instead:** Every test with async code must be `async`. Every promise must be `await`ed or returned.

### Hardcoded timeouts as synchronization
**Looks like:** `await new Promise(r => setTimeout(r, 500))` to "wait for the thing to finish."
**Fails:** Flaky on slow CI, wastes time on fast machines. The 500ms assumption breaks.
**Do instead:** Wait for the actual condition: `waitFor(() => expect(el).toBeVisible())`, or mock timers with `vi.useFakeTimers()`.

### Not cleaning up async state between tests
**Looks like:** A fetch mock set in one test bleeds into the next because `afterEach` clears the wrong thing.
**Fails:** Test order dependency. Tests pass alone, fail in suite.
**Do instead:** `afterEach(() => { vi.restoreAllMocks(); cleanup(); })` — reset everything.

---

## Flakiness Anti-Patterns

### Narrow thresholds in statistical / timing tests
**Looks like:** `expect(avg).toBeCloseTo(50, 1)` on a random distribution. Passes 90% of the time.
**Fails:** Flaky by design. Will fail in CI eventually.
**Do instead:** Use wide margins — test that values fall within a range, not a precise value. Add retry-once for inherently probabilistic behavior. See `statistical-distribution.md`.

### Relying on test execution order
**Looks like:** Test B depends on a side effect from Test A (shared mutable state, shared DB rows).
**Fails:** Run tests in isolation or random order and half the suite collapses.
**Do instead:** Each test sets up and tears down its own state. `beforeEach` for setup, `afterEach` for cleanup.

### Timer-based polls without fake timers
**Looks like:** Testing a polling function by waiting real milliseconds.
**Fails:** Slow and non-deterministic.
**Do instead:** `vi.useFakeTimers()` / `jest.useFakeTimers()`, then `vi.advanceTimersByTime(N)`.

---

## Coverage Anti-Patterns

### Chasing coverage % over meaningful tests
**Looks like:** 95% coverage but all tests are happy path with no assertions on error states.
**Fails:** Coverage says a line was executed, not that it was tested correctly.
**Do instead:** Prioritize: complex logic > error paths > integration points > trivial getters.

### Writing tests for trivial code
**Looks like:** Testing a getter `getUser() { return this.user }` or a constant export.
**Fails:** Wastes time, inflates test count, adds maintenance burden.
**Do instead:** Test logic that can break: branching, transformations, side effects, error handling.

### No tests on the integration seams
**Looks like:** Unit tests for every function but nothing tests that A calls B with the right args and uses the response correctly.
**Fails:** Individual units pass, integration is broken.
**Do instead:** At least one integration test per major data flow: input → transform → output → side effect.

---

## Meta Anti-Patterns

### Assuming tests prove correctness
**Real meaning of passing tests:** "No test found a bug." Not: "No bugs exist."
**Risk:** Overconfident QA report leads to false confidence before a release.
**Do instead:** Note coverage gaps explicitly. A passing suite with 3 tests covering 50 functions is not a clean bill of health.

### Not reading existing tests before writing new ones
**Looks like:** Duplicated test cases, conflicting setups, inconsistent mocking patterns.
**Fails:** Test suite becomes incoherent. Maintenance nightmare.
**Do instead:** Phase 2 is mandatory — read ALL existing tests before writing a single new one.

---

## Lessons from Real Runs

### dailytoolsforall.com (Next.js 14 static, 2026-05-04)

- **Parity grep missing digits**: pattern `[a-z][a-z-]+` silently skips slugs like `base64-encoder` (contains digit). Parity checks for slug matching must use `[a-z0-9][a-z0-9-]+` or equivalent. Found during R-4 registry/renderer parity check — reported false FAIL that wasn't real.

- **Orphan component files after tool removal**: when tools are removed from registry + ToolRenderer, source component files in `components/tools/` are often not deleted. They accumulate silently as dead code. On complex projects with many tools, scan for component files with no corresponding registry entry and flag them as a dedicated check. Found: `EmailHeaderAnalyzer.tsx`, `JsonTreeViewer.tsx`, `InvoiceGenerator.tsx`, `LoremIpsumGenerator.tsx` — all unreachable.

- **AI discovery file drift (llms.txt, sitemap, etc.)**: manually maintained discovery/index files go stale when new tools are added only to the source registry. `llms.txt` claimed 27 tools but listed 26 — `windows-event-viewer` was added to registry but never to the discovery file. Any project with a manually maintained tool list needs an explicit cross-check against the source of truth (registry, DB, etc.) — not just a count check.

- **Zero test coverage on complex binary parsers**: a 731-line DataView binary parser (`lib/evtx-parser.ts`) went to production with 7+ distinct bugs, all caught only by manual inspection and live `.evtx` file testing. No automated tests existed. Binary format parsing (custom protocols, file formats, binary RPC) is the highest-ROI area for unit tests because: (1) bugs are invisible without the right input, (2) fixes regress easily, (3) pure functions are trivially testable with crafted `ArrayBuffer`s. Always flag missing test infra as CRITICAL gap on parser-heavy projects.

### Luni (React/Vite/Vitest, 2026-04-02)
- Suite selected without env check → speech/camera suites loaded with no jsdom mock setup → wasted tests
- Statistical tests used `toBeCloseTo` with tight precision → flaky on CI → switched to range assertions
- Phase 5 failure diagnosis was "test is wrong or code is wrong" → not actionable → classification checklist added
- Policy tests buried in LOW confidence → missed every run → elevated to always-on
- No before/after test count in report → couldn't tell what was new vs existing → before/after added to Phase 6
