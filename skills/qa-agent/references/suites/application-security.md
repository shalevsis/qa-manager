# Application Security Suite

## When to apply
Apply when testing any API endpoint, form input, authentication flow, or user-facing data rendering. Run against all environments that handle user data.

## What to test

- Protected endpoints return 401/403 without a valid auth token
- Accessing another user's resource by changing an ID returns 403 or the correct user's data only
- User-supplied input rendered in the DOM is HTML-escaped, not injected as raw markup
- State-changing endpoints reject requests missing a CSRF token or with an unexpected Origin header
- Session cookies carry HttpOnly, Secure, and SameSite=Strict or Lax flags
- Passwords and tokens never appear in URL query strings
- Sensitive values (card numbers, passwords, tokens) are absent from application log output
- Oversized request bodies are rejected with 413, not a crash or hang
- Redirect parameters cannot forward users to external domains
- Rate-limited endpoints return 429 after the allowed request count; client back-off is exercised

## Key patterns

**Auth bypass**
```
GET /api/resource/123          # no Authorization header
expect(response.status).toBe(401 or 403)
```

**IDOR**
```
token = login(userA)
resourceId = create_resource(userB)
GET /api/resource/{resourceId} with userA token
expect(response.status).toBe(403)   # or response body belongs to userA only
```

**XSS**
```
input = '<script>alert(1)</script>'
POST /api/profile  { bio: input }
GET  /profile page
expect(page.innerHTML).not.toContain('<script>')
expect(page.innerHTML).toContain('&lt;script&gt;')   # escaped
```

**CSRF**
```
POST /api/transfer  (no CSRF token, Origin: https://evil.example)
expect(response.status).toBe(403)
```

**Cookie flags**
```
response.headers['set-cookie'].forEach(cookie => {
  expect(cookie).toMatch(/HttpOnly/i)
  expect(cookie).toMatch(/Secure/i)
  expect(cookie).toMatch(/SameSite=(Strict|Lax)/i)
})
```

**Sensitive data in URLs**
```
# Capture outbound request URLs during login/payment
expect(requestUrl).not.toMatch(/password=/)
expect(requestUrl).not.toMatch(/token=/)
```

**Input size limit**
```
POST /api/endpoint  body: 'A'.repeat(10_000_000)
expect(response.status).toBe(413)
```

**Open redirect**
```
GET /auth/callback?redirect=https://evil.example
expect(response.headers.location).not.toMatch(/evil\.example/)
```

**Rate limiting**
```
for i in 1..N+1:
  POST /api/login  { username, password }
expect(lastResponse.status).toBe(429)
expect(lastResponse.headers['retry-after']).toBeDefined()
```

## Common gaps

- Testing IDOR only with sequential IDs — also test UUIDs and indirect references (slugs, handles)
- Checking the cookie flag on the login response only — verify flags on every Set-Cookie header across the app
- Forgetting that 302 redirects can leak tokens in the Referer header even if not in the URL directly
- Not asserting that the rate-limit counter resets after the retry window, causing false failures on re-runs
- Skipping log assertion — sensitive data in logs is often the only gap after other controls are in place
- Missing the case where CSRF protection is applied to JSON endpoints but not to multipart/form-data variants

---

## Extended Vulnerability Checks

### SSRF (Server-Side Request Forgery)

The server fetches a URL supplied by the user. An attacker can point this at internal services (metadata endpoints, databases, admin consoles) that are not reachable from the internet.

**Grep patterns:**
```bash
grep -rn "requests\.get\|requests\.post\|fetch(\|axios\.\|http\.get\|urllib\.request" --include="*.py" --include="*.js" --include="*.ts"
# Then check whether the URL argument is derived from user input (request params, body fields)
grep -rn "user_url\|target_url\|redirect_url\|webhook\|callback_url\|image_url\|feed_url" --include="*.py" --include="*.js"
```

**Test:**
```python
def test_ssrf_internal_host_is_blocked(client):
    # Attempt to fetch the cloud metadata endpoint via a user-supplied URL
    resp = client.post('/api/fetch-url', json={'url': 'http://169.254.169.254/latest/meta-data/'})
    assert resp.status_code in (400, 403, 422)

def test_ssrf_localhost_is_blocked(client):
    for host in ['http://localhost:8080/admin', 'http://127.0.0.1/internal', 'http://0.0.0.0/']:
        resp = client.post('/api/fetch-url', json={'url': host})
        assert resp.status_code in (400, 403, 422), f"SSRF not blocked for {host}"

def test_ssrf_allowlisted_domain_is_permitted(client):
    resp = client.post('/api/fetch-url', json={'url': 'https://allowed-partner.example.com/data'})
    assert resp.status_code == 200
```

### XXE (XML External Entity)

XML parsers that resolve external entities allow an attacker to read local files or make server-side requests by embedding `<!ENTITY xxe SYSTEM "file:///etc/passwd">` in uploaded XML.

**Grep patterns:**
```bash
grep -rn "xml\|etree\|lxml\|minidom\|expat\|SAXParser\|DOMParser" --include="*.py" --include="*.js"
# Flag: check whether resolve_entities / no_network / forbid_dtd options are set
grep -rn "resolve_entities\|load_dtd\|no_network\|forbid_dtd" --include="*.py"
```

**Test:**
```python
XXE_PAYLOAD = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root><data>&xxe;</data></root>"""

def test_xxe_entity_not_resolved(client):
    resp = client.post(
        '/api/import-xml',
        data=XXE_PAYLOAD,
        content_type='application/xml'
    )
    # Must not return contents of /etc/passwd
    assert 'root:' not in resp.text
    assert resp.status_code in (200, 400, 422)  # parsed safely or rejected, never leaks
```

### Insecure deserialization

`pickle`, `marshal`, and `eval` on untrusted input allow arbitrary code execution. Any object deserialized from user-supplied bytes can run `__reduce__` or equivalent hooks.

**Grep patterns:**
```bash
grep -rn "pickle\.loads\|pickle\.load\|marshal\.loads\|eval(\|exec(\|yaml\.load(" --include="*.py"
# Flag any that take input from request.body, request.data, query params, or file uploads
```

**Test:**
```python
import pickle, os

class Exploit:
    def __reduce__(self):
        return (os.system, ('touch /tmp/pwned',))

def test_pickle_deserialization_blocked(client):
    payload = pickle.dumps(Exploit())
    resp = client.post(
        '/api/load-session',
        data=payload,
        content_type='application/octet-stream'
    )
    assert resp.status_code in (400, 403, 415, 422)
    assert not os.path.exists('/tmp/pwned'), "arbitrary code execution via pickle"
```

### Path traversal

`../` sequences in user-supplied file paths let attackers read or write files outside the intended directory.

**Grep patterns:**
```bash
grep -rn "open(\|send_file\|send_from_directory\|readFile\|createReadStream\|fs\.read" --include="*.py" --include="*.js" --include="*.ts"
# Check if filename/path argument is derived from user input without normalization
grep -rn "request\.args\['file'\]\|req\.params\.filename\|req\.query\.path" --include="*.py" --include="*.js"
```

**Test:**
```python
import pytest

@pytest.mark.parametrize("path", [
    "../etc/passwd",
    "..%2Fetc%2Fpasswd",
    "....//....//etc/passwd",
    "%2e%2e%2fetc%2fpasswd",
])
def test_path_traversal_is_blocked(client, path):
    resp = client.get(f'/api/files/{path}')
    assert resp.status_code in (400, 403, 404), f"path traversal not blocked for: {path}"
    assert 'root:' not in resp.text
```

### Open redirect

A redirect URL accepted from a query parameter without validation lets attackers craft links that appear legitimate but forward users to phishing pages.

**Grep patterns:**
```bash
grep -rn "redirect(\|HttpResponseRedirect\|res\.redirect\|location:" --include="*.py" --include="*.js"
grep -rn "next=\|redirect=\|return_to=\|url=" --include="*.py" --include="*.js" --include="*.html"
```

**Test:**
```python
@pytest.mark.parametrize("target", [
    "https://evil.example.com",
    "//evil.example.com",
    "https://evil.example.com@trusted.example.com",
    "javascript:alert(1)",
])
def test_open_redirect_blocked(client, target):
    resp = client.get(f'/auth/callback?next={target}', allow_redirects=False)
    location = resp.headers.get('location', '')
    assert not location.startswith('https://evil.example.com'), f"open redirect to: {location}"
    assert not location.startswith('//evil.example.com'), f"protocol-relative redirect: {location}"
    assert not location.lower().startswith('javascript:')
```

### Timing attacks on secret comparison

Using `==` to compare tokens or MACs leaks timing information — the comparison short-circuits on the first differing byte, allowing an attacker to brute-force the secret one byte at a time.

**Grep patterns:**
```bash
grep -rn "== token\|token ==\|== secret\|secret ==\|== signature\|signature ==" --include="*.py" --include="*.js"
grep -rn "compare_digest\|hmac\.compare_digest\|crypto\.timingSafeEqual" --include="*.py" --include="*.js"
# Absence of compare_digest near token/signature comparisons is the red flag
```

**Test (structural — assert constant-time comparison is used):**
```python
import hmac, inspect, importlib

def test_token_comparison_uses_constant_time(app_module):
    source = inspect.getsource(app_module.verify_token)
    assert 'compare_digest' in source or 'hmac.compare_digest' in source, \
        "verify_token must use hmac.compare_digest, not =="
```

### Dependency confusion

If your project uses internal package names (e.g., `mycompany-utils`) that are not published on PyPI or npm, an attacker can publish a malicious package with the same name on the public registry. Package managers that check public registries first will install the attacker's version.

**Grep patterns:**
```bash
# Check for internal package names in requirements that have no public registry equivalent
grep -rn "mycompany\|internal-\|private-\|corp-" requirements*.txt package.json pyproject.toml
# Verify these packages are pinned to internal registry URLs in .npmrc / pip.conf
grep -rn "registry\|index-url\|extra-index-url" .npmrc pip.conf setup.cfg pyproject.toml
```

**Test (CI check — assert internal packages resolve only to internal registry):**
```python
def test_internal_packages_use_private_registry(pip_config):
    internal_pkgs = ['mycompany-auth', 'mycompany-utils']
    for pkg in internal_pkgs:
        source = pip_config.get_index_for(pkg)
        assert 'pypi.org' not in source, \
            f"{pkg} resolves from public PyPI — dependency confusion risk"
```

### Prototype pollution (JavaScript)

Merging user-supplied JSON keys like `__proto__` or `constructor.prototype` into a plain object pollutes `Object.prototype`, affecting all objects in the process.

**Grep patterns:**
```bash
grep -rn "Object\.assign\|\.\.\.req\.body\|\_.merge\|deepmerge\|extend(" --include="*.js" --include="*.ts"
# Check whether user-supplied keys are sanitized before merging
grep -rn "__proto__\|constructor\[.prototype.\]\|prototype\[" --include="*.js" --include="*.ts"
```

**Test:**
```js
it('prototype pollution via __proto__ is blocked', async () => {
  const payload = JSON.parse('{"__proto__": {"polluted": true}}');

  await request(app)
    .post('/api/settings')
    .send(payload)
    .expect((res) => {
      expect(res.status).not.toBe(500);
    });

  // Prototype must not be polluted
  expect({}.polluted).toBeUndefined();
});

it('prototype pollution via constructor.prototype is blocked', async () => {
  await request(app)
    .post('/api/settings')
    .send({ 'constructor': { 'prototype': { 'polluted': true } } })
    .expect((res) => {
      expect({}.polluted).toBeUndefined();
    });
});
```

### Mass assignment

Passing `request.body` or `**kwargs` directly to an ORM create/update call lets attackers set fields they should not control — e.g., `is_admin`, `role`, `account_balance`.

**Grep patterns:**
```bash
grep -rn "Model\.create(req\.body\|\.update(req\.body\|\.save(request\.data\|\*\*request\.json\|\*\*kwargs" --include="*.py" --include="*.js" --include="*.ts"
grep -rn "from_dict\|from_json\|update_from_request" --include="*.py"
# Check whether an explicit allowlist of fields is applied before the ORM call
```

**Test:**
```python
def test_mass_assignment_cannot_set_admin_flag(client, regular_user_token):
    resp = client.patch(
        '/api/profile',
        json={'name': 'Alice', 'is_admin': True, 'role': 'superuser'},
        headers={'Authorization': f'Bearer {regular_user_token}'}
    )
    assert resp.status_code in (200, 422)
    profile = client.get('/api/profile', headers={'Authorization': f'Bearer {regular_user_token}'}).json()
    assert profile['is_admin'] is False, "mass assignment allowed privilege escalation"
    assert profile['role'] != 'superuser'
```

### Unvalidated file upload execution

If uploaded files are stored in a web-accessible directory and served with their original extension (e.g., `.php`, `.py`, `.sh`), the server may execute them when a request is made to the upload URL.

**Grep patterns:**
```bash
grep -rn "UPLOAD_FOLDER\|MEDIA_ROOT\|upload_to\|multer\|formidable\|busboy" --include="*.py" --include="*.js" --include="*.ts"
# Check whether the upload path is web-accessible (under /static, /media, /public)
grep -rn "app\.use('/uploads'\|STATIC_URL\|/media/\|/public/uploads" --include="*.py" --include="*.js"
# Check whether extension validation is enforced
grep -rn "\.endswith\|path\.extname\|splitext\|mimetype\|content.type" --include="*.py" --include="*.js"
```

**Test:**
```python
def test_php_upload_is_rejected(client, auth_token):
    fake_php = (b'<?php system($_GET["cmd"]); ?>', 'shell.php', 'application/octet-stream')
    resp = client.post(
        '/api/upload',
        data={'file': fake_php},
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert resp.status_code in (400, 415, 422), "executable file upload was not rejected"

def test_upload_directory_does_not_execute_scripts(client, upload_dir, auth_token):
    # Upload a benign .txt file that contains PHP code
    payload = b'<?php echo "executed"; ?>'
    resp = client.post(
        '/api/upload',
        data={'file': (payload, 'test.txt', 'text/plain')},
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    file_url = resp.json().get('url')
    if file_url:
        fetch = client.get(file_url)
        # Response should be the raw bytes served as text/plain, not PHP output
        assert fetch.text == payload.decode(), "server executed uploaded script content"
        assert fetch.headers.get('content-type', '').startswith('text/plain')
