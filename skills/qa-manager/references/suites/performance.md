# Performance Test Suite

## When to apply
Use when a component has timers, subscriptions, large data sets, or known re-render sensitivity. Run these tests alongside unit tests — they catch regressions invisible to functional tests.

## What to test
- Component renders only the expected number of times (no extra renders, no infinite loop)
- Debounced handlers do not fire until the specified delay has elapsed
- Throttled handlers fire at most once per interval under rapid input
- `setInterval` and `setTimeout` are cleared when the component unmounts
- `requestAnimationFrame` callbacks are cancelled on unmount
- Event listeners added on mount are removed on unmount
- Rendering a large list does not grow heap memory unboundedly (no leak)
- Virtualized/paginated list loads the correct next page when the user scrolls to the boundary
- Bundle imports: no heavy dependency is pulled in that is not exercised by the feature
- Memoization (`memo`, `useMemo`, `useCallback`) prevents re-renders when props are unchanged

## Key patterns

**Render count with spy/fake**
```
let renderCount = 0
const Component = () => { renderCount++; return <div /> }
render(<Component prop={stable} />)
// Re-render with same props
render(<Component prop={stable} />)
assert renderCount === 1   // memoized: no second render
```

**Fake timers for debounce/throttle**
```
vi.useFakeTimers()
fireEvent.input(el, { target: { value: 'x' } })
assert handler.callCount === 0    // not yet
vi.advanceTimersByTime(300)       // debounce delay
assert handler.callCount === 1
vi.useRealTimers()
```

**Interval cleanup on unmount**
```
const setIntervalSpy = vi.spyOn(global, 'setInterval')
const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
const { unmount } = render(<PollingComponent />)
const id = setIntervalSpy.mock.results[0].value
unmount()
assert clearIntervalSpy.calledWith(id)
```

**rAF cleanup on unmount**
```
const rafSpy = vi.spyOn(global, 'requestAnimationFrame')
const cafSpy = vi.spyOn(global, 'cancelAnimationFrame')
const { unmount } = render(<AnimatedComponent />)
unmount()
assert cafSpy.called
```

**Pagination boundary**
```
scrollTo(listEnd)
await nextTick()
assert apiCalls === 2           // second page fetched
assert visibleItems.length === PAGE_SIZE * 2
```

## Common gaps
- Timers tested with `setTimeout(fn, 0)` real delays instead of fake timers — tests become flaky
- `setInterval` cleared by component but spy assertion missed because ID is not captured
- Memory leak test skipped for large lists — only functional correctness verified
- Debounce test advances time but forgets to flush microtask queue before asserting
- Bundle size regression not caught because no size-limit check in CI
- `useEffect` dependency array omission causing re-render loop only visible at runtime, not in unit test
