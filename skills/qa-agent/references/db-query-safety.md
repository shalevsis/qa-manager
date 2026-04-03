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
