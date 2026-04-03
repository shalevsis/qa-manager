# Loop Safety Suite

## When to apply
Apply when the codebase contains while loops, recursive functions, polling loops, retry loops, generator/iterator patterns, or any logic that could theoretically run forever. Detect with: grep for `while True`, `while (true)`, `for(;;)`, recursive function calls, `.retry(`, `do {`.

## What to test

- Every `while` loop has a condition that is guaranteed to become false (counter increment, flag set, collection exhausted)
- Recursive functions have a reachable base case that terminates for all valid inputs
- Retry loops have a maximum attempt count that is always enforced — not just when an exception is caught
- Polling loops check a stop/cancel signal on every iteration, not just at entry
- Loops that iterate over mutable collections do not modify the collection during iteration (concurrent modification)
- Generator functions that yield infinitely are only consumed with an explicit limit or `break`
- Loop counters are not reset inside the loop body (accidental infinite reset)
- Nested loops have correct outer break/continue propagation (inner break doesn't accidentally exit outer)
- Event-driven loops (e.g. game loops, animation frames) are stopped when the component/window unmounts
- Loop timeout: any loop that could run long has a wall-clock timeout as a backstop

## Key patterns

**Max-iteration guard**
```
MAX_ITER = 1000
count = 0
while condition:
    count += 1
    if count > MAX_ITER:
        raise RuntimeError("loop exceeded max iterations — likely infinite")
    do_work()
```

**Test: retry loop enforces max attempts**
```python
def test_retry_loop_exhausts_and_raises():
    calls = []
    def always_fail():
        calls.append(1)
        raise ConnectionError("fail")

    with pytest.raises(Exception):
        retry_with_backoff(always_fail, max_attempts=5)

    assert len(calls) == 5  # exactly 5, not infinite
```

**Test: recursive base case reached for edge inputs**
```python
def test_recursive_flatten_empty_list():
    assert flatten([]) == []

def test_recursive_flatten_single_item():
    assert flatten([1]) == [1]

def test_recursive_flatten_deeply_nested():
    # Should not raise RecursionError
    deep = [[[[[1]]]]]
    assert flatten(deep) == [1]
```

**Test: stop signal exits poll loop within one cycle**
```python
def test_poll_loop_exits_on_stop(monkeypatch):
    import threading
    stop = threading.Event()
    monkeypatch.setattr("myapp.fetch", lambda: [])
    t = threading.Thread(target=myapp.poll_loop, args=(stop,), daemon=True)
    t.start()
    time.sleep(0.05)
    stop.set()
    t.join(timeout=2)
    assert not t.is_alive(), "poll_loop did not stop after stop event"
```

**Test: collection not modified during iteration**
```python
def test_no_modification_during_iteration():
    items = [1, 2, 3, 4, 5]
    result = []
    # Safe: iterate over a copy if removal is needed
    for item in list(items):
        if item % 2 == 0:
            items.remove(item)
        result.append(item)
    assert result == [1, 2, 3, 4, 5]  # all items seen, no skip
```

**Test: generator consumed with explicit limit**
```js
function* infiniteSequence() {
  let n = 0;
  while (true) yield n++;
}

it('consumes generator safely with take limit', () => {
  const gen = infiniteSequence();
  const result = take(gen, 10);
  expect(result).toHaveLength(10);
  expect(result[9]).toBe(9);
});
```

**Test: animation/rAF loop cancelled on unmount**
```js
it('cancels animation loop on unmount', () => {
  const cafSpy = vi.spyOn(global, 'cancelAnimationFrame');
  const { unmount } = render(<AnimatedComponent />);
  unmount();
  expect(cafSpy).toHaveBeenCalled();
});
```

## Common gaps
- Retry loop has `max_attempts` parameter but the loop condition doesn't actually use it — it only breaks on success
- Recursive function handles `[]` but not `None` — base case is incomplete
- Stop signal checked only at loop entry, not mid-sleep — loop sleeps 60s and ignores stop for that duration
- Generator passed to code that assumes it's finite — no `take()` or `islice()` guard
- Nested loop: `break` in inner loop intended to exit outer loop — silently continues outer
- Wall-clock timeout added as a comment ("TODO: add timeout") but never implemented
