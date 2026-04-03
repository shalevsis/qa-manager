# Auth & Session Suite

## When to apply
Use when the feature involves login, logout, token management, protected routes, or role-based access. Apply to any flow that gates content behind identity.

## What to test
- Login success stores token/session and redirects to intended destination
- Login failure displays a user-facing error (wrong credentials, locked account)
- Logout clears token, session cookie, and any in-memory state
- Unauthenticated request to a protected endpoint redirects to login (not 401 raw error)
- Token refresh succeeds before expiry and the user stays logged in
- Expired token triggers re-authentication flow, not an unhandled crash
- RBAC: role A cannot access role B's resource (returns 403, not 500)
- Concurrent sessions: second login invalidates or coexists depending on policy
- Remember-me: session persists after browser restart when opted in
- Remember-me absent: session ends when browser closes

## Key patterns

**Login success — token stored**
```
POST /auth/login  → 200
expect(storage.get('token')).toBeDefined()
expect(currentPath).toBe('/dashboard')
```

**Login failure — error visible**
```
POST /auth/login  → 401
expect(screen.getByRole('alert')).toHaveTextContent(/invalid/i)
expect(storage.get('token')).toBeNull()
```

**Logout — state cleared**
```
logout()
expect(storage.get('token')).toBeNull()
expect(currentPath).toBe('/login')
```

**Protected route — unauthenticated redirect**
```
// No token present
navigate('/dashboard')
expect(currentPath).toBe('/login')
```

**Token refresh**
```
// Intercept refresh endpoint, return new token
expect(originalRequest).toBeRetriedWithNewToken()
```

**RBAC — forbidden resource**
```
GET /admin/users  (as viewer role)  → 403
expect(screen.getByText(/not authorized/i)).toBeInTheDocument()
```

## Common gaps
- Forgot to clear in-memory state (Redux/Zustand store) on logout — token gone but user data lingers
- Refresh race condition: two parallel requests both trigger a refresh; only one should win
- Redirect-after-login: returning user lands on `/login` instead of original destination
- Remember-me tested only at login, not verified after actual browser restart simulation
- RBAC tested only at UI level — backend enforcement not verified separately
- Concurrent sessions: no assertion that previous session token is invalidated
- Token stored in `localStorage` on shared device — threat model not considered in test scope notes
