# GraphQL Suite

## When to apply
Use when the feature communicates with a GraphQL API, whether via Apollo, urql, React Query with a GQL client, or raw fetch. Apply to both query and mutation flows.

## What to test
- Query returns data in the expected shape and UI renders it correctly
- Loading state is shown while the request is in flight
- Error state is shown when the server returns errors or the network fails
- Mutation updates the server and triggers a UI refresh (refetch or cache write)
- Optimistic update is applied immediately and reverts cleanly on failure
- Pagination: next page appends or replaces results; cursor/offset advances correctly
- Variables are constructed correctly before the request is sent
- Auth header (Bearer token or cookie) is included with every request
- Partial errors (data + errors in same response) are handled, not silently dropped

## Key patterns

**Query shape & loading**
```
// Mock: delay then resolve
expect(loadingIndicator).toBeInTheDocument()
await waitForElementToBeRemoved(loadingIndicator)
expect(screen.getByText(mockData.title)).toBeInTheDocument()
```

**Query error state**
```
// Mock: return { errors: [{ message: 'Not found' }] }
expect(screen.getByRole('alert')).toHaveTextContent(/not found/i)
```

**Mutation — cache update**
```
// After mutation resolves, list should include new item
// without a full page reload
await userEvent.click(submitButton)
expect(await screen.findByText(newItemName)).toBeInTheDocument()
```

**Optimistic update — revert on failure**
```
// Mock mutation to reject
// Optimistic item appears, then disappears after rejection
expect(screen.getByText(optimisticName)).toBeInTheDocument()
await waitFor(() =>
  expect(screen.queryByText(optimisticName)).not.toBeInTheDocument()
)
expect(screen.getByRole('alert')).toBeInTheDocument()
```

**Variables sent correctly**
```
// Intercept the request body
expect(requestBody.variables).toEqual({ id: '42', limit: 10 })
```

**Auth header present**
```
expect(requestHeaders['authorization']).toMatch(/^Bearer /)
```

**Cursor pagination**
```
// After "load more", endCursor from page 1 is passed as `after` in page 2
expect(page2Variables.after).toBe(page1.pageInfo.endCursor)
```

## Common gaps
- Partial error response (200 with `errors` array) treated as success — data rendered despite errors
- Optimistic item not removed from cache on rollback, causing ghost entries
- Loading spinner never dismissed when query errors (component waits for `data` that never arrives)
- Variables not updated when props/filters change — stale query sent
- Auth header missing on mutation requests (only added to queries)
- Pagination `hasNextPage: false` not respected — "load more" button still active
- Subscription teardown not tested — listeners accumulate across navigations
