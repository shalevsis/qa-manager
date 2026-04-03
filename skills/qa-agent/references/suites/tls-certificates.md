# TLS & Certificate Suite

## When to apply
Apply when the project serves or consumes HTTPS, uses certificate pinning (mobile apps), runs behind an internal CA, or has TLS configuration that could be misconfigured in production. TLS bugs are silent in development and catastrophic in production.

## What to test

**Certificate validation**
- Expired certificate — connection rejected with a clear TLS error, app does not crash or proceed insecurely
- Not-yet-valid certificate (`notBefore` in the future) — rejected correctly
- Certificate chain incomplete (missing intermediate CA) — validation fails, not silently accepted
- Root CA not in trust store — custom/internal CA requires explicit trust store configuration; not bypassed
- Wildcard certificate (`*.example.com`) — valid for `sub.example.com`, invalid for `example.com` itself and `sub.sub.example.com`
- Subject Alternative Name (SAN) — certificate uses SAN, not CN only (CN-only rejected by modern browsers/clients)
- Hostname mismatch — certificate issued for `api.example.com` rejected when connecting to `www.example.com`
- Self-signed certificate — rejected in production; only accepted in test environments with an explicit, scoped override

**TLS configuration**
- Minimum TLS version enforced — TLS 1.0 and 1.1 connections rejected by server
- Weak cipher suites disabled — `RC4`, `3DES`, `NULL`, `EXPORT` ciphers not negotiated
- Forward secrecy enabled — ECDHE or DHE key exchange used (session keys not recoverable from private key)
- HSTS header present — `Strict-Transport-Security` with `max-age` ≥ 31536000 (1 year) on all HTTPS responses
- HSTS `includeSubDomains` set where appropriate
- No HTTP fallback — redirected HTTP requests go to HTTPS; no content served over plain HTTP
- OCSP stapling enabled — cert revocation status included in TLS handshake

**Certificate pinning (mobile/native apps)**
- Pinned certificate matches server's current certificate — connection succeeds
- Pin mismatch detected and connection refused — not silently ignored
- Backup pin present — primary pin rotated, backup pin allows continuity without app update
- Pin rotation tested — cert renewed without breaking existing app versions in the field

**Certificate revocation**
- Revoked certificate rejected — CRL or OCSP check performed and honored
- OCSP responder unreachable — defined behavior: fail-open (allow) or fail-closed (deny) documented and tested
- Soft-fail vs hard-fail revocation configured intentionally

**Development safety**
- `NODE_TLS_REJECT_UNAUTHORIZED=0` absent from all non-test environment configs
- `verify=False` (Python requests) absent from production code paths
- TLS verification disabled only via explicit test flag, never via environment variable leak
- Internal CA certificate provisioned in CI/Docker — tests do not disable TLS to work around missing cert
- No hardcoded `http://` URLs in production configuration files

**Mixed content**
- HTTPS page does not load any HTTP sub-resources (images, scripts, fonts, API calls)
- Mixed content blocked by browser is detected in E2E tests, not just manual review
- `Content-Security-Policy: upgrade-insecure-requests` header present where appropriate

## Key patterns

**Python — custom CA bundle (requests)**
```python
import requests

session = requests.Session()
session.verify = "/path/to/internal-ca-bundle.crt"  # never False in production
response = session.get("https://internal.service.example.com/health")
assert response.status_code == 200
```

**Python — expired cert rejected**
```python
import pytest, requests

def test_expired_cert_rejected():
    with pytest.raises(requests.exceptions.SSLError):
        requests.get("https://expired.badssl.com/", timeout=5)
```

**Node.js — rejectUnauthorized with custom CA**
```js
const https = require("https");
const fs = require("fs");

const options = {
  hostname: "internal.service.example.com",
  path: "/health",
  rejectUnauthorized: true,          // must never be false in production
  ca: fs.readFileSync("internal-ca.crt"),
};

https.request(options, (res) => {
  expect(res.statusCode).toBe(200);
}).end();
```

**Node.js — expired cert rejected**
```js
const https = require("https");

test("rejects expired certificate", (done) => {
  const req = https.request({ hostname: "expired.badssl.com", rejectUnauthorized: true }, () => {
    done(new Error("Expected TLS error, got response"));
  });
  req.on("error", (err) => {
    expect(err.code).toMatch(/CERT_HAS_EXPIRED|UNABLE_TO_VERIFY_LEAF_SIGNATURE/);
    done();
  });
  req.end();
});
```

**HSTS header — integration test**
```js
// JS (supertest / fetch)
const res = await request(app).get("/").set("Host", "example.com");
expect(res.headers["strict-transport-security"]).toMatch(/max-age=3153600/);
expect(res.headers["strict-transport-security"]).toContain("includeSubDomains");
```
```python
# Python (requests)
response = requests.get("https://example.com/")
hsts = response.headers.get("Strict-Transport-Security", "")
assert "max-age=" in hsts
max_age = int(re.search(r"max-age=(\d+)", hsts).group(1))
assert max_age >= 31536000, f"HSTS max-age too short: {max_age}"
```

**Playwright — intercept certificate errors**
```js
const { chromium } = require("playwright");

test("certificate error page shown for invalid cert", async () => {
  const browser = await chromium.launch({ ignoreHTTPSErrors: false });
  const page = await browser.newPage();
  let tlsError = false;
  page.on("requestfailed", (req) => {
    if (req.failure().errorText.includes("ERR_CERT")) tlsError = true;
  });
  await page.goto("https://self-signed.badssl.com/").catch(() => {});
  expect(tlsError).toBe(true);
  await browser.close();
});
```

**Grep — find disabled TLS verification in codebase**
```
# Find verify=False in Python files
grep -rn "verify\s*=\s*False" --include="*.py" .

# Find rejectUnauthorized: false in JS/TS files
grep -rn "rejectUnauthorized\s*:\s*false" --include="*.{js,ts,mjs}" .

# Find NODE_TLS_REJECT_UNAUTHORIZED set to 0
grep -rn "NODE_TLS_REJECT_UNAUTHORIZED" . | grep -v "\.test\." | grep -v "spec\."
```

**Assert NODE_TLS_REJECT_UNAUTHORIZED not set in production env**
```js
test("NODE_TLS_REJECT_UNAUTHORIZED is not disabled in production config", () => {
  const prodEnv = require("./config/env.production.js");
  expect(prodEnv.NODE_TLS_REJECT_UNAUTHORIZED).not.toBe("0");
  expect(process.env.NODE_TLS_REJECT_UNAUTHORIZED).not.toBe("0");
});
```

## Common gaps
- `NODE_TLS_REJECT_UNAUTHORIZED=0` added to fix a CI problem and never removed — production TLS verification disabled
- Internal CA cert not in Docker image — every CI run disables TLS verification instead of provisioning the cert
- Self-signed cert accepted in staging, `SKIP_TLS_VERIFY` flag forgotten in production deploy
- Certificate pinning implemented without a backup pin — cert rotation causes 100% of deployed app versions to break
- HSTS `max-age` set to 300 (5 minutes) instead of 31536000 — effectively useless
- OCSP stapling configured but never tested — revocation check fails silently
- Wildcard cert `*.example.com` assumed to cover `example.com` — login page on apex domain breaks
- Mixed content only checked manually — automated tests run against `http://localhost` and never catch HTTPS-to-HTTP downgrade
