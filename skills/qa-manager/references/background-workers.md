# Pattern: Background Workers & Polling

**When to apply:** Project has background threads, polling loops, `setInterval` workers, cron-style tasks, or adaptive retry logic. Covers Python `threading.Thread`, Node `setInterval`/`setTimeout`, async task queues.

**How to detect:** grep for `threading.Thread`, `_poll_loop`, `setInterval`, `while True:` + `sleep`, `asyncio.create_task`.

---

## 1. Adaptive backoff as pure math (no threads needed)

Extract the interval-doubling logic into a pure function and test it without spawning threads. This catches inverted logic, wrong caps, wrong reset conditions.

```python
# The pattern being tested (extract from poll loop):
def next_interval(current: int, base: int, no_update: bool, max_interval: int = 3600) -> int:
    if no_update:
        return min(current * 2, max_interval)
    return base
```

```python
# Tests — pure function, instant, no mocking needed
def test_backoff_doubles_on_idle():
    assert next_interval(900, 900, no_update=True) == 1800

def test_backoff_resets_on_activity():
    assert next_interval(3600, 900, no_update=False) == 900

def test_backoff_never_exceeds_max():
    cur = 900
    for _ in range(20):
        cur = next_interval(cur, 900, no_update=True)
    assert cur == 3600

def test_backoff_sequence():
    base = 900
    cur = base
    syncs = [True, True, False, True, True, True]  # True = no_update
    intervals = []
    for no_update in syncs:
        intervals.append(cur)
        cur = next_interval(cur, base, no_update)
    assert intervals == [900, 1800, 3600, 900, 1800, 3600]
```

---

## 2. Idle skip — zero-result sync produces no side effects

When a sync/poll returns 0 items, the system should skip expensive operations (DB writes, downstream calls). Test with a mock.

```python
def test_empty_sync_skips_db_write(monkeypatch):
    writes = []
    monkeypatch.setattr("myapp.db_upsert", lambda rows: writes.extend(rows))

    # patch fetch to return empty
    monkeypatch.setattr("myapp.fetch_updates", lambda: [])
    result = myapp.sync_once()

    assert result.get("skipped") is True
    assert writes == []  # no DB writes when nothing fetched
```

---

## 3. Stop event respected within one cycle

The poll loop should check a stop event and exit within one polling cycle — not hang indefinitely. Test by setting the event and running the loop in a thread.

```python
import threading, time

def test_poll_loop_stops_on_event(monkeypatch):
    stop = threading.Event()
    monkeypatch.setattr("myapp.fetch_updates", lambda: [])  # instant

    t = threading.Thread(target=myapp.poll_loop, args=(stop,), daemon=True)
    t.start()
    time.sleep(0.1)   # let it enter the loop
    stop.set()
    t.join(timeout=2)
    assert not t.is_alive(), "poll_loop did not stop within 2 seconds"
```

---

## 4. One-shot background task doesn't block the caller

```python
def test_background_task_is_non_blocking():
    import time
    start = time.time()
    myapp.queue_background_analysis()  # should return immediately
    elapsed = time.time() - start
    assert elapsed < 0.1, "background task blocked caller"
```

---

## 5. Rate cap — background task doesn't fire too often

```python
def test_auto_analyze_rate_limited(monkeypatch):
    calls = []
    monkeypatch.setattr("myapp._run_analysis", lambda: calls.append(1))
    monkeypatch.setattr("myapp._last_analysis_time", time.time())  # just ran

    myapp.maybe_auto_analyze()  # should be rate-limited
    assert calls == []  # not called again within the rate window
```

---

## JS/Node equivalent

```js
// Mock setInterval — test callback is called with correct interval
jest.useFakeTimers();

it('polls on the configured interval', () => {
  const spy = jest.fn().mockResolvedValue({ count: 0 });
  startPoller(spy, 15 * 60 * 1000);  // 15 min

  jest.advanceTimersByTime(15 * 60 * 1000);
  expect(spy).toHaveBeenCalledTimes(1);

  jest.advanceTimersByTime(15 * 60 * 1000);
  expect(spy).toHaveBeenCalledTimes(2);
});

it('stops polling on cleanup', () => {
  const spy = jest.fn().mockResolvedValue({});
  const stop = startPoller(spy, 5000);
  stop();
  jest.advanceTimersByTime(10000);
  expect(spy).toHaveBeenCalledTimes(0);
});
```
