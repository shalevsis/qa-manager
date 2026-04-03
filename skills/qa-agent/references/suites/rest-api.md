# Pattern: REST API Contracts

**When to apply:** Project exposes HTTP endpoints — Flask, Express, FastAPI, Django, Koa, etc. Apply to every route. These are the minimum tests any API should have.

**How to detect:** grep for `@app.route`, `app.get(`, `router.post(`, `@router.`, `path(` in the codebase.

---

## 1. Status code contracts

Every endpoint should return the right HTTP status for every meaningful input class.

```python
# Python/pytest — Flask example
def test_get_items_ok(client):
    assert client.get("/api/items").status_code == 200

def test_get_item_not_found(client):
    assert client.get("/api/items/99999").status_code == 404

def test_post_missing_required_field(client):
    assert client.post("/api/items", json={}).status_code == 400

def test_post_auth_key_missing(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert client.post("/api/analyze", json={"id": 1}).status_code == 400

def test_post_auth_key_invalid(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "bad-key")
    # depending on implementation: 401, 403, or 400 — pick one, nail it down
    assert client.post("/api/analyze", json={"id": 1}).status_code in (400, 401, 403)
```

```js
// Node/supertest
it('GET /items → 200', async () => {
  const res = await request(app).get('/api/items');
  expect(res.status).toBe(200);
});

it('POST /items missing body → 400', async () => {
  const res = await request(app).post('/api/items').send({});
  expect(res.status).toBe(400);
});
```

---

## 2. Response shape

Assert required keys exist. Don't just assert status=200 — the shape is part of the contract.

```python
def test_items_response_shape(client):
    resp = client.get("/api/items")
    data = resp.json
    assert "items" in data          # top-level key
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        for key in ("id", "status", "created_at"):
            assert key in item, f"missing key: {key}"

def test_stats_required_keys(client):
    data = client.get("/api/stats").json
    for key in ("total", "by_status", "last_sync"):
        assert key in data
```

---

## 3. Missing / invalid params → 400 with useful error

```python
def test_missing_required_param_returns_400(client):
    resp = client.post("/api/analyze", json={})  # missing required field
    assert resp.status_code == 400
    # Error message should hint at the problem — not just "Bad Request"
    assert "error" in resp.json or "message" in resp.json

def test_wrong_type_param(client):
    resp = client.get("/api/items?limit=abc")
    assert resp.status_code in (200, 400)  # never 500

def test_negative_limit(client):
    resp = client.get("/api/items?limit=-1")
    assert resp.status_code in (200, 400)
```

---

## 4. Auth env var absent → 400, not 500

When the error is "API key not configured", the endpoint should return 400 with an actionable message — not crash with a 500 KeyError.

```python
def test_api_key_missing_returns_400_not_500(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post("/api/analyze", json={"mode": "stale"})
    assert resp.status_code == 400
    body = resp.json
    assert "API_KEY" in str(body).upper()  # message names the missing var

def test_empty_input_returns_400(client):
    resp = client.post("/api/analyze", json={"ticket_ids": []})
    assert resp.status_code == 400
```

---

## 5. Type coercion safety

Flask's `request.args.get("hours", type=float)` returns `None` for non-numeric strings — use this pattern. Test the boundary.

```python
@pytest.mark.parametrize("val,expect_ok", [
    ("7", True),
    ("0", True),
    ("0.5", True),
    ("abc", True),   # coercion silently returns None → treated as "no filter"
    ("-1", True),    # negative: depends on app logic
    ("9999999", True),
])
def test_numeric_param_coercion(client, val, expect_ok):
    resp = client.get(f"/api/items?hours={val}")
    assert (resp.status_code == 200) == expect_ok
```

---

## 6. Idempotency / safe methods

GET should never mutate state. POST should be safe to retry on empty input.

```python
def test_get_is_idempotent(client):
    r1 = client.get("/api/stats").json
    r2 = client.get("/api/stats").json
    assert r1["total"] == r2["total"]  # no side effects from reads
```
