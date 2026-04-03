# Routing & Navigation Tests

## When to apply
Use whenever the application uses client-side routing (SPA or hybrid) and enforces access control, URL-driven state, or redirect logic.

## What to test
- Protected routes redirect unauthenticated users to the login page
- Authenticated users can access protected routes without redirect
- Unknown paths render a 404 / not-found page
- Browser back button restores previous page state (scroll position, list contents)
- Deep links load the correct content without requiring prior navigation
- Query parameters are parsed and reflected in component behavior
- Redirect after login targets the originally requested URL, not a hardcoded default
- Navigation triggered mid-async operation (e.g. mid-fetch) does not crash or leave stale state

## Key patterns

### Protected route — unauthenticated
```js
renderWithRouter(<App />, { initialEntries: ['/dashboard'], authState: null });
expect(screen.getByTestId('login-page')).toBeInTheDocument();
expect(window.location.pathname).toBe('/login');
```

### Protected route — authenticated
```js
renderWithRouter(<App />, { initialEntries: ['/dashboard'], authState: fakeUser });
expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
```

### 404 page
```js
renderWithRouter(<App />, { initialEntries: ['/does-not-exist'] });
expect(screen.getByText(/page not found/i)).toBeInTheDocument();
```

### Deep link — correct content loaded
```js
renderWithRouter(<App />, { initialEntries: ['/items/42'] });
await screen.findByText('Item 42 Title');
```

### Query params parsed
```js
renderWithRouter(<App />, { initialEntries: ['/search?q=widget&page=2'] });
await screen.findByText('Results for "widget"');
expect(screen.getByLabelText(/page/i)).toHaveValue('2');
```

### Redirect after login preserves intended URL
```js
renderWithRouter(<App />, { initialEntries: ['/settings'], authState: null });
await loginAs(fakeUser);
expect(window.location.pathname).toBe('/settings'); // not '/home'
```

### Navigation during async — no crash
```js
const { unmount } = renderWithRouter(<App />, { initialEntries: ['/slow-page'] });
// navigate away before fetch completes
act(() => navigateTo('/other-page'));
unmount();
// no "can't perform state update on unmounted component" error
```

## Common gaps
- Not testing the redirect destination encodes the original path (e.g. `?next=/settings`)
- Skipping the "already authenticated user visits /login" redirect
- Not asserting 404 for paths that are one character off from a valid route
- Back button test only checks URL, not that component state was preserved
- No test for navigating away while a mutation (POST/PUT) is in flight
- Query param tests that only check the URL string, not the rendered output
- Missing test for route params with special characters (spaces, slashes, unicode)
