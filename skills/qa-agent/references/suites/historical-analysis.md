# Suite: Historical Analysis

## When to apply
Use this suite when the app stores a time series of data points and derives trends, statistics, or rankings from that history.

## What to test

- New data point added to the history is immediately retrievable
- Trend classified correctly for an ascending series, descending series, and flat series
- Statistical summary values correct: mean, median, percentile, and outlier detection
- Heuristic ranking is deterministic: same inputs always produce the same rank
- History pruning: oldest entries removed when the record limit is reached; newest entries retained
- Data consistency: history reflects the correct state after a sequence of add/remove/update operations
- Empty history: UI renders without error, analysis returns a zero-entry or "no data" state gracefully
- Corrupted single entry: bad record does not crash the full analysis; remaining records processed normally
- Cross-session persistence: history survives an app reload or process restart

## Key patterns

```
// Add and retrieve
addDataPoint({ value: 42, timestamp: now() })
expect(getHistory().last()).toMatchObject({ value: 42 })

// Trend detection
expect(detectTrend([1, 2, 3, 4])).toBe('ascending')
expect(detectTrend([4, 3, 2, 1])).toBe('descending')
expect(detectTrend([3, 3, 3, 3])).toBe('flat')

// Statistical summary
const stats = computeStats([10, 20, 30, 40, 100])
expect(stats.mean).toBeCloseTo(40)
expect(stats.median).toBe(30)
expect(stats.p90).toBeCloseTo(100)
expect(stats.outliers).toContain(100)

// Deterministic ranking
const rank1 = computeRank(sampleInputs)
const rank2 = computeRank(sampleInputs)
expect(rank1).toEqual(rank2)

// Pruning
fillHistory({ count: MAX_RECORDS + 5 })
expect(getHistory()).toHaveLength(MAX_RECORDS)
expect(getHistory().first().timestamp).toBe(sixthOldest.timestamp)

// Empty history
clearHistory()
expect(renderHistoryView).not.toThrow()
expect(analysisResult).toMatchObject({ status: 'no_data' })

// Corrupted entry
injectCorruptedEntry({ index: 2 })
expect(() => computeStats(getHistory())).not.toThrow()
expect(computeStats(getHistory()).count).toBe(validEntryCount)

// Cross-session persistence
addDataPoint({ value: 99 })
reloadApp()
expect(getHistory().last()).toMatchObject({ value: 99 })
```

## Common gaps

- Trend detection tested only with perfectly monotonic series; real-world noisy series (e.g., [1, 3, 2, 4]) not covered
- Percentile computed as a simple array index rather than a standard interpolation formula; off-by-one for small datasets
- Ranking determinism not tested across multiple calls — non-determinism only appears under load or with equal-score ties
- Pruning removes newest entries instead of oldest, but test only checks total count, not which entries remain
- Empty history: component renders but throws a divide-by-zero error in the statistics function
- Corrupted entry causes `JSON.parse` to throw, which propagates and crashes the entire history load
- Cross-session persistence tested only in memory (same process); actual storage serialization/deserialization not exercised
- Outlier detection threshold hardcoded in the test rather than derived from the production configuration, causing false passes
