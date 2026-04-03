# Concurrency Suite

## When to apply
Apply when the project has multiple users, multiple tabs/sessions, background workers writing shared state, or any async operations that could interleave. Detect with: grep for `async`, `await`, `Promise.all`, `threading`, `asyncio`, `concurrent`, `mutex`, `lock`, `queue`, `shared`, `cache`, `session`, database writes from multiple code paths.

## What to test

- Simultaneous writes from two users to the same resource — last writer wins, or merge, or conflict error — whichever is the intended behavior is actually enforced
- Read-while-write: a read that starts before a write completes returns either the old value or the new value — never a partial/corrupt value
- Optimistic locking: a stale update (version mismatch) is rejected with a conflict error, not silently overwritten
- Double-submit: submitting a form or action twice in rapid succession triggers the operation exactly once — not twice
- Race condition on cache: two concurrent requests for uncached data both trigger a fetch — only one should reach the backend (request deduplication / cache stampede protection)
- Concurrent file uploads: multiple files uploaded simultaneously all complete correctly — no interleaved writes, no file corruption
- Session isolation: two users logged in simultaneously do not see each other's data, tokens, or state
- Shared counter or balance: concurrent increments/decrements always result in a consistent final value — no lost updates
- Queue ordering: items processed from a job queue maintain insertion order when order matters; concurrent workers do not process the same item twice
- Background worker + user write to same record: the worker's stale write does not overwrite a newer user write

## Key patterns

**Simultaneous writes — last write wins or conflict**
```python
import threading

def test_concurrent_writes_to_same_record(db):
    record_id = db.create_item(value=0)
    errors = []

    def write(val):
        try:
            db.update_item(record_id, value=val)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=write, args=(1,))
    t2 = threading.Thread(target=write, args=(2,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    final = db.get_item(record_id)
    # Value must be one of the two writers — not 0, not corrupt
    assert final['value'] in (1, 2), f"unexpected value after concurrent write: {final['value']}"
    assert not errors or len(errors) == 1, "more than one write should succeed in last-write-wins"
```

**Optimistic locking — stale update rejected**
```python
def test_optimistic_lock_rejects_stale_update(db):
    item = db.create_item(name="original", version=1)

    # Simulate two clients reading the same version
    client_a_version = item['version']
    client_b_version = item['version']

    # Client A updates first
    db.update_item(item['id'], name="client_a_update", version=client_a_version)

    # Client B tries to update with the old version — should fail
    with pytest.raises(Exception, match="conflict|version mismatch|stale"):
        db.update_item(item['id'], name="client_b_update", version=client_b_version)

    final = db.get_item(item['id'])
    assert final['name'] == "client_a_update"  # Client A's write preserved
```

**Double-submit guard**
```js
it('double-clicking submit only submits once', async () => {
  const submitSpy = vi.fn().mockResolvedValue({ ok: true });
  server.intercept('/api/submit', submitSpy);

  const btn = screen.getByRole('button', { name: /submit/i });
  await userEvent.click(btn);
  await userEvent.click(btn);   // rapid second click

  expect(submitSpy).toHaveBeenCalledTimes(1);
});
```

**Cache stampede protection**
```js
it('concurrent cache misses only trigger one backend fetch', async () => {
  const fetchSpy = vi.fn().mockResolvedValue({ data: 'result' });
  cache.clear();

  // Fire three concurrent requests for the same uncached key
  const [r1, r2, r3] = await Promise.all([
    getData('key-x', fetchSpy),
    getData('key-x', fetchSpy),
    getData('key-x', fetchSpy),
  ]);

  expect(fetchSpy).toHaveBeenCalledTimes(1);  // only one upstream call
  expect(r1).toEqual(r2);
  expect(r2).toEqual(r3);
});
```

**Concurrent increments — no lost updates**
```python
def test_concurrent_increments_no_lost_updates(db):
    counter_id = db.create_counter(value=0)
    threads = []
    n = 50

    def increment():
        db.atomic_increment(counter_id)  # must use atomic op or SELECT FOR UPDATE

    for _ in range(n):
        t = threading.Thread(target=increment)
        threads.append(t)
    for t in threads: t.start()
    for t in threads: t.join()

    final = db.get_counter(counter_id)
    assert final['value'] == n, f"lost updates: expected {n}, got {final['value']}"
```

**Session isolation between users**
```js
it('two simultaneous sessions do not share data', async () => {
  const [userA, userB] = await Promise.all([
    loginAs('user-a@example.com'),
    loginAs('user-b@example.com'),
  ]);

  const [dataA, dataB] = await Promise.all([
    userA.get('/api/profile'),
    userB.get('/api/profile'),
  ]);

  expect(dataA.email).toBe('user-a@example.com');
  expect(dataB.email).toBe('user-b@example.com');
  expect(dataA.id).not.toBe(dataB.id);
});
```

**Queue item not processed twice by concurrent workers**
```python
def test_queue_item_processed_exactly_once(queue):
    queue.enqueue(job_id="job-1", payload={"task": "send_email"})
    processed = []

    def worker():
        job = queue.dequeue()   # must use atomic dequeue (e.g. BRPOPLPUSH or SELECT ... SKIP LOCKED)
        if job:
            processed.append(job['job_id'])

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert processed.count("job-1") == 1, "job processed more than once"
```

**Concurrent file uploads complete without corruption**
```js
it('three simultaneous uploads all complete correctly', async () => {
  const files = [
    new File(['aaa'], 'a.txt', { type: 'text/plain' }),
    new File(['bbb'], 'b.txt', { type: 'text/plain' }),
    new File(['ccc'], 'c.txt', { type: 'text/plain' }),
  ];

  const results = await Promise.all(files.map(f => uploadFile(f)));

  expect(results).toHaveLength(3);
  results.forEach((r, i) => {
    expect(r.status).toBe('success');
    expect(r.filename).toBe(files[i].name);
    expect(r.size).toBe(files[i].size);
  });
});
```

## Common gaps
- Concurrent tests written sequentially in tests — race condition never actually triggered because calls are awaited in order
- Optimistic locking implemented in ORM but not tested — conflict path never executed
- Double-submit guard only disables the button in UI — API has no server-side idempotency key
- Cache deduplication untested — stampede discovered in production under load
- Counter incremented with `UPDATE counter SET value = value + 1` but no test confirms atomicity under concurrent load
- Queue uses `SELECT` then `DELETE` in two steps — two workers can both SELECT the same item before either DELETEs it
- Session isolation tested for data reads but not for write operations — user A's write can land in user B's session under certain middleware configs
