# Pattern: Fixture Factory & Test Isolation

**When to apply:** Tests need a database, file path, environment variable, or external state. Use to ensure tests never share state and never touch production data.

**How to detect:** Project has SQLite/Postgres/MySQL DB, module-level path constants (e.g. `DB_PATH`), or calls `os.environ.get("API_KEY")`.

---

## 1. SQLite tmp_path isolation (Python/pytest)

Each test gets a fresh DB in a temp directory — auto-cleaned after the test. Use `monkeypatch.setattr` to redirect the module-level path constant.

```python
import pytest, sqlite3

@pytest.fixture
def db(tmp_path, monkeypatch):
    """Isolated SQLite DB per test — no shared state, auto-cleaned."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("myapp.DB_PATH", db_path)
    import myapp
    myapp.DB_PATH = db_path   # also patch any cached reference
    myapp.init_db()            # create schema
    yield db_path

@pytest.fixture
def client(db):
    """Flask test client wired to the isolated DB fixture."""
    from myapp import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
```

---

## 2. Record factory function

Build minimal valid records with sensible defaults. Callers override only the fields relevant to the test — keeps tests readable and resilient to schema changes.

```python
# conftest.py
def make_ticket(**kwargs):
    defaults = dict(
        id=1,
        subject="test ticket",
        status="Open",
        priority="Medium",
        group_name="Support",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        conversations="[]",
    )
    return {**defaults, **kwargs}

# Usage in tests — only specify what matters
def test_closed_ticket_not_burning():
    t = make_ticket(status="Closed")
    assert detect_burning(t) == []

def test_urgent_ticket_flagged():
    t = make_ticket(priority="Urgent", subject="site down")
    assert is_high_priority(t)
```

```js
// JS equivalent
const makeItem = (overrides = {}) => ({
  id: 1,
  title: 'test item',
  status: 'open',
  createdAt: '2026-01-01T00:00:00Z',
  ...overrides,
});
```

---

## 3. Insert helper for DB tests

For tests that need actual rows in the DB (not just in-memory dicts), add an insert helper in conftest.

```python
def insert_ticket(db_path, **kwargs):
    """Insert one row into tickets table. Returns inserted id."""
    t = make_ticket(**kwargs)
    conn = sqlite3.connect(db_path)
    cols = ",".join(t.keys())
    placeholders = ",".join("?" * len(t))
    conn.execute(f"INSERT OR REPLACE INTO tickets ({cols}) VALUES ({placeholders})", list(t.values()))
    conn.commit(); conn.close()
    return t["id"]

# Usage
def test_search_returns_matching_row(db):
    insert_ticket(db, id=1, subject="VPN not connecting")
    insert_ticket(db, id=2, subject="unrelated topic")
    result = db_query(search="VPN")
    assert len(result) == 1
    assert result[0]["id"] == 1
```

---

## 4. Environment variable mocking

```python
# Env var present
def test_api_key_present(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    resp = client.post("/api/analyze", json={"mode": "stale"})
    assert resp.status_code != 400  # key found — error is something else

# Env var absent
def test_api_key_absent_returns_400(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.post("/api/analyze", json={"mode": "stale"})
    assert resp.status_code == 400
    assert "API_KEY" in str(resp.json).upper()
```

```js
// Node — mock process.env
const origKey = process.env.API_KEY;
afterEach(() => { process.env.API_KEY = origKey; });

it('missing API key returns 400', async () => {
  delete process.env.API_KEY;
  const res = await request(app).post('/api/analyze').send({ mode: 'stale' });
  expect(res.status).toBe(400);
});
```

---

## 5. Postgres / other DBs

For non-SQLite: use a test database URL, run migrations in a `session`-scoped fixture, and wrap each test in a transaction that rolls back.

```python
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    conn = db_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn)
    yield session
    session.close()
    trans.rollback()
    conn.close()
```
