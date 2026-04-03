# Suite: Statistical Distribution

## When to apply
Apply when the app uses weighted random selection, spaced repetition, A/B splits, or any sampling algorithm. Run when the selection function, weight schema, or weight calculation logic changes.

---

## Flaky test policy — read before writing any statistical test

Statistical tests are inherently probabilistic and will produce false failures if not written carefully. Follow these rules without exception:

1. **Prefer deterministic over probabilistic.** Test the weight calculation function directly (pure math, always deterministic) rather than sampling the selection output. If you can assert `calculateWeight(item) === expectedWeight`, do that instead of running 500 iterations.

2. **Seed the RNG when possible.** If the implementation accepts a seed, always pass one in tests. This makes runs fully reproducible.

3. **Use wide margins.** If you expect a 60% selection rate over 500 trials, set threshold at 45% (not 55%). Use `p < 0.01` confidence, not `p < 0.05`. The cost of a wider margin is a weaker assertion; the cost of a narrow margin is CI noise.

4. **Every statistical test must include a comment** explaining: expected distribution, why the threshold was chosen, and the margin used. Example:
   ```js
   // Expected: ~70% selection rate for high-weight items (weight ratio 7:3)
   // Threshold set at 55% (not 65%) to account for statistical variance at N=500
   // At p<0.01, we'd need >555 out of 1000 to be confident — using 275/500 as threshold
   ```

5. **Retry policy.** If a statistical test fails, re-run it once before marking it as a real failure. Two consecutive failures = genuine issue. One failure = likely statistical noise.

6. **Minimum iterations: 500.** Below 100 is too noisy. Above 2000 slows CI unnecessarily.

## What to test

- Weak/high-weight items are selected more often than strong/low-weight items over many iterations
- Weight inversion bug: a common mistake maps high weight to low probability — verify it goes the right direction
- Uniform distribution when all weights are equal — no item is systematically favored
- Empty input is handled gracefully (no crash, defined return value)
- Single-item input always returns that item regardless of its weight
- Items with weight 0 (or below threshold) are never selected
- Distribution is stable across re-runs (not degenerate — e.g. always returns index 0)

---

## Key patterns

**Core pattern — run N times, assert proportions:**
```js
const ITERATIONS = 500;
const TOLERANCE = 0.10; // allow ±10% of expected proportion

it('selects high-weight items more often than low-weight items', () => {
  const items = [
    { id: 'A', weight: HIGH_WEIGHT },
    { id: 'B', weight: LOW_WEIGHT },
  ];
  const counts = { A: 0, B: 0 };

  for (let i = 0; i < ITERATIONS; i++) {
    const selected = selectWeighted(items);
    counts[selected.id]++;
  }

  const ratioA = counts.A / ITERATIONS;
  const ratioB = counts.B / ITERATIONS;

  // High-weight item should dominate
  expect(ratioA).toBeGreaterThan(ratioB);
  // And roughly match the expected proportion
  const expectedRatioA = HIGH_WEIGHT / (HIGH_WEIGHT + LOW_WEIGHT);
  expect(ratioA).toBeGreaterThan(expectedRatioA - TOLERANCE);
  expect(ratioA).toBeLessThan(expectedRatioA + TOLERANCE);
});
```

**Weight inversion check:**
```js
it('does NOT invert weights (high weight = high probability)', () => {
  const items = [
    { id: 'HEAVY', weight: MAX_WEIGHT },
    { id: 'LIGHT', weight: MIN_WEIGHT },
  ];
  const counts = { HEAVY: 0, LIGHT: 0 };
  for (let i = 0; i < ITERATIONS; i++) {
    counts[selectWeighted(items).id]++;
  }
  expect(counts.HEAVY).toBeGreaterThan(counts.LIGHT);
});
```

**Uniform distribution when all weights equal:**
```js
it('distributes uniformly when all weights are equal', () => {
  const items = Array.from({ length: ITEM_COUNT }, (_, i) => ({
    id: `item_${i}`,
    weight: UNIFORM_WEIGHT,
  }));
  const counts = Object.fromEntries(items.map((item) => [item.id, 0]));
  for (let i = 0; i < ITERATIONS; i++) {
    counts[selectWeighted(items).id]++;
  }
  const expected = ITERATIONS / ITEM_COUNT;
  Object.values(counts).forEach((count) => {
    expect(count).toBeGreaterThan(expected * (1 - TOLERANCE));
    expect(count).toBeLessThan(expected * (1 + TOLERANCE));
  });
});
```

**Edge cases:**
```js
it('returns null (or defined fallback) for empty input', () => {
  expect(selectWeighted([])).toBeNull(); // or toEqual(FALLBACK)
});

it('always returns the only item when input has one element', () => {
  const single = [{ id: 'ONLY', weight: ANY_WEIGHT }];
  for (let i = 0; i < 20; i++) {
    expect(selectWeighted(single).id).toBe('ONLY');
  }
});

it('never selects an item with weight zero', () => {
  const items = [
    { id: 'EXCLUDED', weight: 0 },
    { id: 'INCLUDED', weight: POSITIVE_WEIGHT },
  ];
  for (let i = 0; i < ITERATIONS; i++) {
    expect(selectWeighted(items).id).not.toBe('EXCLUDED');
  }
});
```

---

## Common gaps

- Using too few iterations (< 100) — statistical noise causes flaky passes and false failures
- Not testing the direction of weighting, only that "something is returned"
- Forgetting the weight inversion bug — off-by-one or inverted subtraction is the most common mistake
- Not seeding or controlling randomness in CI — flaky tests that fail ~5% of the time
- Assuming equal-weight uniform distribution without asserting it (silent bias from rounding)
- No test for zero-weight items — they often sneak through and distort proportions
- Not testing what happens when total weight is 0 (all items excluded) — usually a crash
- Threshold set too narrow (55% when expecting 60%) — statistically valid run fails and erodes trust in CI
- No comment explaining threshold rationale — future developer tightens it not knowing why it was wide
- Not retrying once on failure — single flaky failure triggers wasted investigation
