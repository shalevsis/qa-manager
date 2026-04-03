# Pattern: DB Query Safety

**When to apply:** Project builds SQL queries from user-controlled input — filters, search terms, pagination, sort fields. Works with SQLite, Postgres, MySQL. Applicable in Python, Node, Ruby, Go.

**How to detect:** grep for `IN (`, `LIKE`, `f"`, or string concatenation near `WHERE` in query-building code.

---

## 1. Empty-list IN() crash

Building `IN (?,?)` from an empty list produces `IN ()` — a syntax error in most SQL engines. Always guard before appending.

```python
# Python — guard before building IN clause
if status_in:
    q += f" AND status IN ({','.join('?'*len(status_in))})"
    params.extend(status_in)
# else: no filter added — returns all (or return [] immediately if semantics require)
```

```js
// Node — same guard
if (statusIn.length > 0) {
  q += ` AND status IN (${statusIn.map(() => '?').join(',')})`;
  params.push(...statusIn);
}
```

**Test:**
```python
def test_empty_filter_returns_empty_not_crash(db):
    result = db_query(status_in=[])
    assert result == []   # raises OperationalError before fix

def test_single_value_filter_works(db):
    result = db_query(status_in=["Open"])
    assert isinstance(result, list)
```

---

## 2. LIKE metacharacter leak

`%` and `_` are wildcard characters in SQL LIKE. `search="%"` matches every row; `search="_"` matches any single-char value. Escape before building the clause.

```python
# Python — escape LIKE metacharacters
def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

q += " AND subject LIKE ? ESCAPE '\\'"
params.append(f"%{_escape_like(search)}%")
```

```js
// Node
const escapeLike = v => v.replace(/\\/g,'\\\\').replace(/%/g,'\\%').replace(/_/g,'\\_');
q += " AND subject LIKE ? ESCAPE '\\'";
params.push(`%${escapeLike(search)}%`);
```

**Test:**
```python
@pytest.mark.parametrize("term", ["%", "_", "\\", "%_%"])
def test_like_metachar_does_not_match_all(db, populate_two_rows, term):
    result = db_query(search=term)
    # term doesn't appear literally in any row → should return 0, not all rows
    assert len(result) == 0
```

---

## 3. f-string SQL injection (detect + test)

f-strings bypass parameterization. Most risky when the value comes from a URL param.

```bash
# Detect in Python
grep -n 'f".*{[a-z_]*}.*WHERE\|f".*WHERE.*{[a-z_]*}' app.py
grep -n "f'.*{[a-z_]*}.*WHERE" app.py
```

```python
# UNSAFE — hours interpolated directly
q = f"WHERE created_at >= DATETIME('now', '-{hours} hours')"

# SAFE — type-enforced at Flask route level
@app.route("/api/items")
def items():
    hours = request.args.get("hours", type=float)  # "abc" → None
    if hours is not None:
        q += "WHERE created_at >= DATETIME('now', ? || ' hours')"
        params.append(f"-{hours}")
```

**Test:**
```python
@pytest.mark.parametrize("hours", [0, 0.5, 9999, None])
def test_hours_param_boundary(client, hours):
    url = f"/api/items?hours={hours}" if hours is not None else "/api/items"
    assert client.get(url).status_code == 200

def test_hours_string_is_rejected_or_ignored(client):
    assert client.get("/api/items?hours=abc").status_code == 200  # not 500
```

---

## 4. Parametrize safety matrix

```python
@pytest.mark.parametrize("term", [
    "%",           # LIKE wildcard
    "_",           # LIKE single-char wildcard
    "'; DROP TABLE tickets--",  # classic injection
    "\\",          # escape char
    "",            # empty string
    "a" * 1000,    # very long input
])
def test_search_param_safe(client, term):
    resp = client.get(f"/api/items?search={term}")
    assert resp.status_code in (200, 400)  # never 500
    assert isinstance(resp.json, (list, dict))
```

---

## DB Locks & Contention

### SELECT FOR UPDATE and lock acquisition patterns

`SELECT FOR UPDATE` acquires a row-level exclusive lock for the duration of the transaction. Use it when you need to read a row and then update it atomically — the lock prevents another transaction from modifying the row between your read and write.

```sql
-- PostgreSQL: lock the row, then update within the same transaction
BEGIN;
SELECT id, balance FROM accounts WHERE id = 42 FOR UPDATE;
-- perform business logic here
UPDATE accounts SET balance = balance - 100 WHERE id = 42;
COMMIT;
```

```python
# psycopg2
import psycopg2

def transfer(conn, from_id, to_id, amount):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT balance FROM accounts WHERE id = %s FOR UPDATE",
            (from_id,)
        )
        row = cur.fetchone()
        if row['balance'] < amount:
            raise ValueError("insufficient funds")
        cur.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s",
            (amount, from_id)
        )
        cur.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, to_id)
        )
    conn.commit()
```

```python
# SQLAlchemy ORM — with_for_update()
from sqlalchemy import select

with session.begin():
    stmt = select(Account).where(Account.id == 42).with_for_update()
    account = session.execute(stmt).scalar_one()
    account.balance -= 100
```

### Deadlock detection and resolution

A deadlock occurs when transaction A holds a lock on resource X and waits for resource Y, while transaction B holds a lock on resource Y and waits for resource X. Both are stuck indefinitely.

Most databases detect deadlocks automatically and abort one of the transactions with an error (`ERROR: deadlock detected` in PostgreSQL, `ERROR 1213` in MySQL). The aborted transaction must be retried.

**Prevention — always acquire locks in a consistent order:**
```python
# UNSAFE: T1 locks account 1 then 2; T2 locks account 2 then 1 → deadlock possible
def transfer_unsafe(conn, a_id, b_id, amount):
    lock_account(conn, a_id)
    lock_account(conn, b_id)
    ...

# SAFE: always lock the lower ID first
def transfer_safe(conn, a_id, b_id, amount):
    first, second = sorted([a_id, b_id])
    lock_account(conn, first)
    lock_account(conn, second)
    ...
```

**Test — trigger and handle a deadlock:**
```python
import threading
import psycopg2

def test_deadlock_is_raised_not_hung(pg_dsn):
    errors = []

    def txn_a(conn):
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN")
                cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
                # yield to let txn_b lock row 2 first
                import time; time.sleep(0.05)
                cur.execute("SELECT id FROM items WHERE id = 2 FOR UPDATE")
                cur.execute("COMMIT")
        except psycopg2.errors.DeadlockDetected as e:
            errors.append(e)
            conn.rollback()

    def txn_b(conn):
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN")
                cur.execute("SELECT id FROM items WHERE id = 2 FOR UPDATE")
                import time; time.sleep(0.05)
                cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
                cur.execute("COMMIT")
        except psycopg2.errors.DeadlockDetected as e:
            errors.append(e)
            conn.rollback()

    conn_a = psycopg2.connect(pg_dsn)
    conn_b = psycopg2.connect(pg_dsn)

    t1 = threading.Thread(target=txn_a, args=(conn_a,))
    t2 = threading.Thread(target=txn_b, args=(conn_b,))
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    # At least one transaction must have been aborted — not both hanging
    assert len(errors) >= 1, "expected deadlock detection, got a hang"
```

### Lock timeout: transactions waiting too long should time out

A transaction that waits indefinitely for a lock can stall your entire application. Set a lock timeout so waiting transactions fail fast and predictably.

```sql
-- PostgreSQL: fail immediately if lock cannot be acquired
SET lock_timeout = '2s';
SELECT id FROM orders WHERE id = 99 FOR UPDATE;
-- raises: ERROR: canceling statement due to lock timeout

-- MySQL equivalent
SET innodb_lock_wait_timeout = 2;
```

```python
# psycopg2 — set lock timeout per connection or per transaction
def test_lock_timeout_raises_not_hangs(pg_dsn):
    import psycopg2

    # Connection 1: hold the lock
    conn1 = psycopg2.connect(pg_dsn)
    cur1 = conn1.cursor()
    cur1.execute("BEGIN")
    cur1.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")

    # Connection 2: attempt to acquire the same lock with a short timeout
    conn2 = psycopg2.connect(pg_dsn)
    cur2 = conn2.cursor()
    cur2.execute("SET lock_timeout = '500ms'")

    with pytest.raises(psycopg2.errors.LockNotAvailable):
        cur2.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")

    cur1.execute("ROLLBACK")
    conn1.close(); conn2.close()
```

### Row-level vs table-level locks

| Lock type | Scope | Use when |
|---|---|---|
| Row-level (`SELECT FOR UPDATE`, `FOR SHARE`) | Single rows | Concurrent writes to different rows are common; only protect specific rows being modified |
| Table-level (`LOCK TABLE`) | Entire table | Bulk operations (truncate, schema migration, full-table rewrite) where row-level locks would be too expensive |
| Advisory locks | Application-defined | Mutual exclusion outside of row/table scope — e.g., distributed cron jobs, cache rebuilds |

**Test that row-level locks do not block concurrent writes to different rows:**
```python
def test_row_lock_does_not_block_other_rows(pg_dsn):
    import threading, psycopg2

    completed = []

    def lock_row_1():
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
            import time; time.sleep(0.2)  # hold lock
            cur.execute("COMMIT")

    def write_row_2():
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("UPDATE items SET name = 'updated' WHERE id = 2")
            cur.execute("COMMIT")
        completed.append('row_2_done')

    t1 = threading.Thread(target=lock_row_1)
    t2 = threading.Thread(target=write_row_2)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert 'row_2_done' in completed  # row 2 was not blocked by row 1's lock
```

### SKIP LOCKED pattern for job queue workers

`SKIP LOCKED` lets multiple workers dequeue jobs concurrently without contention. Each worker atomically claims a row that no other worker has locked, skipping any rows currently locked by another worker.

```sql
-- PostgreSQL: each worker claims exactly one unclaimed job
BEGIN;
SELECT id, payload
FROM jobs
WHERE status = 'pending'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;

-- mark as in-progress and commit
UPDATE jobs SET status = 'processing', worker_id = $1 WHERE id = $2;
COMMIT;
```

```python
# psycopg2 implementation
def dequeue_job(conn, worker_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, payload FROM jobs
            WHERE status = 'pending'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(
            "UPDATE jobs SET status = 'processing', worker_id = %s WHERE id = %s",
            (worker_id, row['id'])
        )
    conn.commit()
    return row

def test_skip_locked_no_duplicate_processing(pg_dsn):
    import threading, psycopg2

    # Seed one job
    conn = psycopg2.connect(pg_dsn)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO jobs (status, payload) VALUES ('pending', '{}') RETURNING id")
        job_id = cur.fetchone()[0]
    conn.commit()

    claimed = []

    def worker(worker_id):
        c = psycopg2.connect(pg_dsn)
        job = dequeue_job(c, worker_id)
        if job:
            claimed.append(job['id'])
        c.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert claimed.count(job_id) == 1, f"job {job_id} was claimed {claimed.count(job_id)} times"
```

### Long-running transactions holding locks

A transaction that holds locks for a long time blocks all other writers on those rows. Monitor and test for this by asserting that lock-holding transactions complete within a time bound.

```python
def test_transaction_completes_within_time_limit(pg_dsn):
    import time, psycopg2

    conn = psycopg2.connect(pg_dsn)
    start = time.monotonic()

    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
        # ... do work ...
        cur.execute("COMMIT")

    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"transaction held lock for {elapsed:.2f}s — too long"
```

**Detecting long-running transactions in PostgreSQL:**
```sql
-- Find transactions running longer than 30 seconds
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
  AND (now() - pg_stat_activity.query_start) > interval '30 seconds';
```

### Test patterns using two concurrent DB connections

The general pattern for any lock contention test:

```python
import threading
import psycopg2

def test_lock_contention_pattern(pg_dsn):
    """
    Template: connection 1 holds a lock, connection 2 attempts to acquire it.
    Verify the observed behavior (block, timeout, or skip).
    """
    ready = threading.Event()    # signals that conn1 has acquired its lock
    done = threading.Event()     # signals conn1 to release its lock
    results = {}

    def conn1_worker():
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
            ready.set()          # lock is held — let conn2 proceed
            done.wait(timeout=3) # hold until test is done
            cur.execute("ROLLBACK")
        conn.close()

    def conn2_worker():
        ready.wait(timeout=3)    # wait until conn1 holds the lock
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor() as cur:
            cur.execute("SET lock_timeout = '200ms'")
            try:
                cur.execute("SELECT id FROM items WHERE id = 1 FOR UPDATE")
                results['outcome'] = 'acquired'
            except psycopg2.errors.LockNotAvailable:
                results['outcome'] = 'timed_out'
        conn.close()
        done.set()

    t1 = threading.Thread(target=conn1_worker)
    t2 = threading.Thread(target=conn2_worker)
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    assert results.get('outcome') == 'timed_out'
```

### Detecting lock contention in tests

**PostgreSQL — inspect active locks:**
```sql
-- Show all current locks and the queries holding/waiting for them
SELECT
    l.pid,
    l.granted,
    l.mode,
    l.locktype,
    a.query,
    a.state,
    now() - a.query_start AS wait_duration
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted
ORDER BY wait_duration DESC;
```

**MySQL — inspect InnoDB lock status:**
```sql
SHOW ENGINE INNODB STATUS;
-- Look for the TRANSACTIONS section: "LOCK WAIT" lines indicate contention
```

**In tests — assert no lock waits are present after a test completes:**
```python
def assert_no_lock_waits(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*) FROM pg_locks WHERE NOT granted
        """)
        waiting = cur.fetchone()[0]
    assert waiting == 0, f"{waiting} transactions are still waiting for locks"
```

### Advisory locks for application-level mutual exclusion

Advisory locks are lightweight, application-defined locks that exist outside the row/table model. Use them for distributed cron jobs, one-at-a-time background tasks, or any mutual exclusion that does not map to a specific database row.

```sql
-- Session-level advisory lock (released when connection closes or explicitly unlocked)
SELECT pg_try_advisory_lock(12345);   -- returns true if acquired, false if already held

-- Transaction-level advisory lock (released at end of transaction)
SELECT pg_try_advisory_xact_lock(12345);
```

```python
# psycopg2 — advisory lock for a distributed cron job
CRON_LOCK_KEY = 99001  # arbitrary integer key agreed upon by all instances

def run_if_leader(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (CRON_LOCK_KEY,))
        acquired = cur.fetchone()[0]
    if not acquired:
        return  # another instance is already running this job
    try:
        do_scheduled_work()
    finally:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (CRON_LOCK_KEY,))

def test_advisory_lock_prevents_duplicate_cron_run(pg_dsn):
    import threading, psycopg2

    acquired = []

    def try_acquire(worker_id):
        conn = psycopg2.connect(pg_dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (CRON_LOCK_KEY,))
            if cur.fetchone()[0]:
                acquired.append(worker_id)
        # intentionally do NOT release — held for test duration
        conn.close()

    threads = [threading.Thread(target=try_acquire, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(acquired) == 1, f"advisory lock acquired by {len(acquired)} workers simultaneously"
```
