# Search & Filter Suite

## When to apply
Use when the feature includes a text search box, filter controls (dropdowns, checkboxes, date pickers), or a combination. Apply to any list or data table that can be narrowed by user input.

## What to test
- Search input is debounced — a request is not fired on every keystroke
- Empty query shows all results or a defined empty/default state (not a crash)
- Multiple filters applied together use AND logic and return only matching items
- Active filters and search query are reflected in the URL (shareable, bookmarkable)
- Clearing all filters restores the full unfiltered list
- Zero-results state renders a helpful message, not a blank screen
- Special characters in search query do not throw errors or break the UI
- Very long query string is handled gracefully (truncated display or capped request)
- Filter state is restored correctly when navigating back via browser history

## Key patterns

**Debounce — only one request after typing**
```
jest.useFakeTimers()
userEvent.type(searchInput, 'hello')        // 5 keystrokes
jest.advanceTimersByTime(300)               // debounce window
expect(fetchSpy).toHaveBeenCalledTimes(1)
expect(fetchSpy).toHaveBeenCalledWith(expect.objectContaining({ q: 'hello' }))
```

**Empty query — full list shown**
```
userEvent.clear(searchInput)
await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(totalCount))
```

**Filter combination (AND)**
```
// Select category=Books and inStock=true
// Only items matching BOTH should appear
expect(results.every(r => r.category === 'Books' && r.inStock)).toBe(true)
```

**URL reflects filters**
```
userEvent.type(searchInput, 'coffee')
selectFilter('category', 'Drinks')
expect(window.location.search).toContain('q=coffee')
expect(window.location.search).toContain('category=Drinks')
```

**Clear filters — full list restored**
```
userEvent.click(clearAllButton)
expect(window.location.search).toBe('')
expect(screen.getAllByRole('listitem')).toHaveLength(totalCount)
```

**No results state**
```
// Mock API returns []
expect(screen.getByText(/no results/i)).toBeInTheDocument()
expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
```

**Special characters — no crash**
```
userEvent.type(searchInput, '<script>alert(1)</script>')
expect(screen.queryByRole('alert')).not.toBeInTheDocument() // no error boundary triggered
```

**Very long query**
```
userEvent.type(searchInput, 'a'.repeat(500))
expect(fetchSpy.mock.calls[0][0].q.length).toBeLessThanOrEqual(255)
// or: expect(screen.getByRole('textbox')).toHaveAttribute('maxlength')
```

## Common gaps
- Debounce not tested — only final state verified, multiple inflight requests possible in production
- Filter state lost on browser back navigation (filters not read from URL on mount)
- OR vs AND logic not validated — overlapping results sneak through incorrect logic
- URL encoding not tested — spaces or `&` in query corrupt the query string
- "No results" branch skipped — blank white space shipped without a message
- Stale results shown when a slow first request resolves after a faster second one (no request cancellation)
- Filter counts/badges not updated after clearing one filter while others remain active
