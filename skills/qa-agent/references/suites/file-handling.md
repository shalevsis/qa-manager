# File Handling Test Suite

## When to apply
Use when the feature involves uploading, downloading, or deleting files. Applies to any input[type=file], drag-and-drop upload zone, or server-side file endpoint.

## What to test
- File type is validated against an allowlist of MIME types (not just file extension)
- File size limit is enforced before upload begins (client) and on the server (server)
- Selecting multiple files via multi-select input captures all selected files
- Upload progress indicator reflects actual bytes transferred (not just a spinner)
- Cancelling an in-progress upload stops the request and resets the UI cleanly
- Download response includes correct `Content-Disposition` filename and `Content-Type` MIME type
- Deleting a file removes it from the server (not just the UI) and cannot be re-fetched
- An empty file (0 bytes) is handled without crashing — rejected or accepted per spec
- A corrupt/truncated file is rejected with a user-readable error, not a silent failure or crash

## Key patterns

**MIME allowlist (not extension only)**
```
allowed = ['image/png', 'image/jpeg', 'application/pdf']
assert file.type in allowed          # MIME check
assert file.name.split('.')[-1] ...  # extension check is insufficient alone
```

**Size limit before upload**
```
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
assert file.size <= MAX_BYTES before network call is made
```

**Download headers**
```
Content-Disposition: attachment; filename="report.pdf"
Content-Type: application/pdf
```

**Cancel cleans up**
```
controller = AbortController()
fetch(url, { signal: controller.signal })
controller.abort()
# Assert: no pending request, progress reset to 0, UI back to idle state
```

**Server-side delete verification**
```
DELETE /files/{id}          → 204
GET    /files/{id}          → 404  # must verify server actually removed it
```

## Common gaps
- Validating only the file extension, which users can spoof (e.g. `malware.exe` renamed to `malware.jpg`)
- Not testing size enforcement on the server — a bypassed client check allows oversized uploads
- Progress bar that jumps to 100% immediately instead of tracking `onprogress` events
- After cancel, the partial upload remaining accessible on the server
- Missing `Content-Type` or wrong MIME on download causing browser to open instead of save
- No test for 0-byte file — often causes a divide-by-zero in progress calculation
- Corrupt file accepted silently because only size/type are checked, not content integrity
