# Error Handling & Graceful Degradation Tests

## When to apply
Use whenever code interacts with external systems (API, DB, file system) or any path that can throw. Apply at both unit and UI level.

## What to test
- try/catch boundaries catch expected error types and do not swallow unexpected ones
- Error boundaries (UI) prevent a subtree crash from taking down the whole app
- Users see a friendly, actionable message — never a raw stack trace
- Retry button triggers the failed operation again and succeeds when the error clears
- Errors are cleared from state / UI once the operation succeeds
- Network errors show an offline / retry state
- Unhandled promise rejections are surfaced (not silently swallowed)
- Error state resets when the user navigates away and returns

## Key patterns

### try/catch — expected error caught
```js
mockApi.getUser.mockRejectedValueOnce(new NotFoundError('User 99'));
const result = await userService.getUser(99);
expect(result).toBeNull(); // graceful fallback, not a throw
```

### try/catch — unexpected errors re-thrown
```js
mockApi.getUser.mockRejectedValueOnce(new TypeError('Unexpected'));
await expect(userService.getUser(99)).rejects.toThrow(TypeError);
```

### Error boundary — subtree crash isolated
```js
render(
  <ErrorBoundary fallback={<div>Something went wrong</div>}>
    <BrokenComponent />
  </ErrorBoundary>
);
expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
expect(screen.queryByTestId('app-shell')).toBeInTheDocument(); // shell still visible
```

### Friendly message — no stack trace
```js
server.use(rest.get('/api/data', (_, res, ctx) => res(ctx.status(500))));
renderPage();
await screen.findByText(/unable to load/i);
expect(screen.queryByText(/at Object\./)).not.toBeInTheDocument();
```

### Retry button works
```js
server.use(rest.get('/api/data', failOnce, thenSucceed));
await screen.findByText(/failed to load/i);
await userEvent.click(screen.getByRole('button', { name: /retry/i }));
await screen.findByText('Expected content');
```

### Network error — offline state shown
```js
server.use(rest.get('/api/data', (_, res) => res.networkError('offline')));
renderPage();
await screen.findByText(/check your connection/i);
```

### Error cleared on success
```js
// first render fails, second succeeds
await userEvent.click(retryButton);
await waitFor(() =>
  expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument()
);
```

### Error state resets on navigation
```js
await triggerErrorState();
navigateTo('/other');
navigateTo('/original');
expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument();
```

## Common gaps
- Only testing that an error message appears, not that it disappears after recovery
- No test confirming a raw stack trace or internal error code is hidden from the user
- Skipping the retry path — only asserting the error state, never the recovery
- Not testing error boundary fallback UI (only happy-path renders)
- Assuming network errors and HTTP 5xx errors are handled by the same code path
- Missing test for partial failure (some items load, one fails) in list/batch fetches
- Not verifying that unrelated parts of the UI remain interactive during an error state
