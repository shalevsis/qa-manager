# LocalStorage State Testing

Use this reference when the app uses `localStorage` as a persistent database (common in offline-first apps, games, learning apps, browser tools).

## What to cover

### 1. Key Regression Test (most important)
If the storage key ever changes, all users silently lose their data. Write a test that **fails loudly** if anyone renames the key:

```typescript
// This is not paranoia — it's the single highest-ROI test for stateful apps
it('uses exactly "my-app-state" as the storage key', () => {
  const spy = vi.spyOn(localStorage, 'setItem');
  saveState({ xp: 10 });
  expect(spy).toHaveBeenCalledWith('my-app-state', expect.any(String));
});
```

### 2. Round-Trip Fidelity
```typescript
it('save + load preserves all data types', async () => {
  const state = { xp: 150, badges: ['first_word'], nested: { seen: 3, correct: 2 }, flag: true };
  await store.save('key', state);
  const loaded = await store.load('key', null);
  expect(loaded).toEqual(state);
});
```

### 3. Missing Key Returns Fallback
```typescript
it('returns fallback when key does not exist', async () => {
  localStorage.clear();
  const result = await store.load('missing-key', { xp: 0 });
  expect(result).toEqual({ xp: 0 });
});
```

### 4. Corrupted JSON Resilience
```typescript
it('returns fallback instead of throwing when JSON is corrupted', async () => {
  localStorage.setItem('key', '{{not valid json}}');
  const result = await store.load('key', { xp: 0 });
  expect(result).toEqual({ xp: 0 }); // graceful degradation, not crash
});
```

### 5. State Migration Resilience
Apps evolve — new fields get added. Existing users have old state without those fields. Test that old state loads without crashing and new fields default gracefully:

```typescript
it('loads v1 state missing new fields without crashing', async () => {
  // Simulate a user who saved state before "wordStats" was added
  localStorage.setItem('key', JSON.stringify({ xp: 100, badges: [] }));
  const result = await store.load('key', DEFAULT_STATE);
  // App should merge/default missing fields, not throw
  expect(result.xp).toBe(100);
  expect(result.wordStats).toBeDefined(); // defaulted, not undefined
});
```

### 6. Delete Removes the Key
```typescript
it('del removes the item from storage', async () => {
  await store.save('key', { xp: 5 });
  await store.del('key');
  expect(localStorage.getItem('key')).toBeNull();
});
```

## Mocking in Vitest/Jest

```typescript
// Use the built-in jsdom localStorage mock — no setup needed in most projects
// For custom behavior:
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});
```

## Key patterns to watch for

- **Silent overwrites**: saving twice with the same key — does the second save win correctly?
- **Quota exceeded**: `localStorage.setItem` throws `DOMException` when storage is full — is it caught?
- **Cross-tab state**: does the app handle `storage` events if another tab writes to the same key?
- **Default state shape**: if `DEFAULT_STATE` is the fallback, test that it contains all required keys
