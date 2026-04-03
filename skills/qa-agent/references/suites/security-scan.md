# Suite: Security Scan

## When to apply
Run before any release or when new user-input paths, API endpoints, or dependencies are added. Apply whenever secrets or sensitive data handling is introduced or modified.

---

## What to test

- No secrets (API keys, tokens, passwords) committed in source or config files
- User input is sanitized before being rendered into the DOM (XSS)
- User input is never concatenated directly into database queries (SQL injection)
- Hardcoded credentials are absent from all config, env sample, and fixture files
- API responses do not leak sensitive fields (passwords, tokens, internal IDs) to clients
- Known vulnerable dependencies are flagged via audit tooling

---

## Key patterns

**Automated grep for secret patterns:**
```bash
# Run from repo root — tune patterns for your stack
grep -rn \
  -e "api[_-]?key\s*=\s*['\"][^'\"]\{8,\}" \
  -e "password\s*=\s*['\"][^'\"]\{4,\}" \
  -e "secret\s*=\s*['\"][^'\"]\{4,\}" \
  -e "token\s*=\s*['\"][^'\"]\{8,\}" \
  -e "BEGIN (RSA|EC|OPENSSH) PRIVATE KEY" \
  --include="*.js" --include="*.ts" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=.git \
  . && echo "SECRETS FOUND" || echo "Clean"
```

**XSS — assert sanitization before render:**
```js
it('sanitizes user input before rendering', () => {
  const malicious = '<script>alert(1)</script>';
  const result = renderUserContent(malicious);
  expect(result).not.toContain('<script>');
  expect(result).not.toContain('alert(1)');
});
```

**SQL injection — never concatenate input:**
```js
it('uses parameterized query, not string concat', () => {
  // Confirm the query builder receives params separately
  const spy = jest.spyOn(db, 'query');
  fetchRecord(USER_INPUT);
  expect(spy).toHaveBeenCalledWith(
    expect.stringContaining('?'),  // or $1 for pg
    expect.arrayContaining([USER_INPUT])
  );
});
```

**API response does not leak sensitive fields:**
```js
it('omits sensitive fields from public response', async () => {
  const res = await request(app).get('/api/RESOURCE/1');
  expect(res.body).not.toHaveProperty('password');
  expect(res.body).not.toHaveProperty('token');
  expect(res.body).not.toHaveProperty('internalSecret');
});
```

**Dependency audit (CI step):**
```bash
# Node
npm audit --audit-level=high

# Python
pip-audit --desc --fail-on CRITICAL,HIGH
```

---

## Common gaps

- `.env.example` files that contain real working credentials instead of placeholders
- Secrets in test fixture files (treated as "not real" but still committed)
- `console.log` statements that print tokens or full user objects in production paths
- JWT payloads decoded client-side and displayed — payload is not encrypted
- Error responses that include stack traces with file paths or DB schema details
- Audit only run manually, not gated in CI — vulnerabilities age undetected
- Checking only `*.js` files but missing `*.ts`, `*.yaml`, `*.toml` config files
