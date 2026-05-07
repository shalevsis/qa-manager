# Application Security Suite

## When to apply
Apply to any project that accepts user input, renders user-controlled content, handles authentication, manages sessions, or communicates over HTTP. Load this suite on every project — it is always-on regardless of archetype.

## What to test

### Input handling
- All user-supplied strings are validated before use (length, type, allowed chars)
- Inputs that exceed max length are rejected with a clear error, not truncated silently
- Numeric fields reject non-numeric strings and out-of-range values
- File upload fields reject disallowed extensions and verify MIME type independently of filename
- File size limits enforced server-side, not only client-side

### Output encoding
- User-controlled content rendered in HTML is encoded before insertion into the DOM
- Dynamic content inserted via JavaScript uses text-node APIs (e.g., `textContent`, `innerText`) rather than raw HTML insertion methods
- JSON responses served to browsers include correct `Content-Type: application/json` header
- Template engines have auto-escaping enabled — explicit unescaped output only where justified

### Authentication
- Unauthenticated requests to protected routes return 401 or redirect to login — never return data
- Passwords are hashed using an appropriate algorithm (bcrypt, Argon2, scrypt) — never stored in plaintext or reversible encoding
- Login endpoints rate-limit repeated failures
- Session tokens have sufficient entropy (128+ bits)
- Sessions are invalidated on logout (server-side, not only cookie deletion)
- Password reset tokens are single-use and expire within a short window (e.g., 15–60 minutes)

### Session management
- Session cookies have `HttpOnly` and `Secure` flags set
- `SameSite` attribute is set to `Strict` or `Lax` on session cookies
- Session IDs are rotated after privilege escalation (e.g., after login)
- Sessions expire after a configurable inactivity timeout

### State-changing requests (CSRF)
- POST/PUT/PATCH/DELETE endpoints require a server-verified token or use `SameSite=Strict` cookies
- State-changing endpoints reject requests that lack the required token
- GET requests do not perform state changes

### Authorization
- Resource access checks happen server-side on every request — not only on the UI layer
- Users cannot access another user's resources by substituting IDs in the request
- Privilege checks are not based on user-supplied role claims in the request body

### HTTP headers
- `Content-Security-Policy` header present and restricts inline script execution
- `X-Content-Type-Options: nosniff` present
- `X-Frame-Options: DENY` or `SAMEORIGIN` present (or CSP `frame-ancestors`)
- `Strict-Transport-Security` present on HTTPS endpoints
- Server version headers (`Server`, `X-Powered-By`) are suppressed

### Error handling
- Error responses do not leak stack traces, file paths, or internal identifiers to clients
- 404 and 500 responses return generic messages — internal detail logged server-side only
- Validation error responses name the invalid field but not internal implementation detail

### Dependency hygiene
- No known-vulnerable dependency versions in `package.json`, `requirements.txt`, or equivalent
- Lockfile present and committed — dependency versions pinned

## Key patterns

**Test: protected route rejects unauthenticated request**
```python
def test_protected_route_rejects_no_token(client):
    response = client.get("/api/user/profile")
    assert response.status_code == 401

def test_protected_route_rejects_invalid_token(client):
    response = client.get("/api/user/profile",
                          headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
```

```typescript
it('returns 401 for unauthenticated request', async () => {
  const res = await fetch('/api/user/profile');
  expect(res.status).toBe(401);
});
```

**Test: user cannot access another user's resource (IDOR)**
```python
def test_user_cannot_read_other_users_resource(client, user_a_token, user_b_id):
    response = client.get(f"/api/users/{user_b_id}/data",
                          headers={"Authorization": f"Bearer {user_a_token}"})
    assert response.status_code in (403, 404)
```

**Test: input length limit enforced**
```python
def test_input_over_max_length_rejected(client):
    long_input = "a" * 10_001  # exceeds documented 10k char limit
    response = client.post("/api/comments", json={"body": long_input})
    assert response.status_code == 422

def test_input_at_max_length_accepted(client):
    at_limit = "a" * 10_000
    response = client.post("/api/comments", json={"body": at_limit})
    assert response.status_code in (200, 201)
```

**Test: error response does not leak internals**
```python
def test_error_response_no_stack_trace(client):
    response = client.get("/api/nonexistent-endpoint")
    body = response.text
    assert "Traceback" not in body
    assert "/Users/" not in body
    assert "node_modules" not in body
```

**Policy test: no plaintext secret patterns in source**
```python
import re
from pathlib import Path

def test_no_plaintext_credentials_in_source():
    secret_pattern = re.compile(
        r'(?i)(password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{6,}["\']'
    )
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build"}
    violations = []
    for path in Path(".").rglob("*"):
        if any(skip in path.parts for skip in skip_dirs):
            continue
        if path.suffix in (".py", ".js", ".ts", ".env", ".yaml", ".yml", ".json"):
            try:
                text = path.read_text(errors="ignore")
                if secret_pattern.search(text):
                    # Only flag if it doesn't reference env vars
                    for m in secret_pattern.finditer(text):
                        context = text[max(0, m.start()-20):m.end()+20]
                        if "process.env" not in context and "os.environ" not in context:
                            violations.append(f"{path}:{m.start()}")
            except (PermissionError, IsADirectoryError):
                pass
    assert not violations, f"Potential plaintext credentials found: {violations}"
```

**Policy test: HttpOnly + Secure flags on session cookies**
```python
def test_session_cookie_has_security_flags(client):
    response = client.post("/api/login",
                           json={"username": "testuser", "password": "testpass"})
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
```

**Policy test: security headers present**
```python
def test_security_headers_present(client):
    response = client.get("/")
    headers = response.headers
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in headers
```

## Common gaps
- IDOR checks skipped — tests cover happy path but never substitute a different user's ID
- CSRF protection tested only in unit tests against the token validator, never end-to-end
- Session invalidation on logout not tested — cookie deleted client-side but server session remains active
- Error messages tested for correct status code but not for information leakage in the body
- `HttpOnly`/`Secure` cookie flags asserted in code review but never in automated tests
- Security headers checked once at setup and never regression-tested — can be silently removed
- Dependency audit (`npm audit`, `pip-audit`) not part of CI — vulnerable packages accumulate
