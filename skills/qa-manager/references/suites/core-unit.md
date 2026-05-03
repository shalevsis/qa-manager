# Core Unit & Integration Tests

## When to apply
Use for any function, module, or service-level test. Apply whenever you are verifying isolated logic or the contract between two or more collaborating units.

## What to test
- Function contracts: given a known input, assert the exact expected output
- Null / undefined / zero / empty-string inputs do not throw unexpectedly
- Boundary values: off-by-one, max/min numeric limits, empty collections
- Thrown errors: correct type, message, and only under the right conditions
- Pure function determinism: same input always produces same output, no hidden state
- Integration between 2+ modules: real wiring, not just mocks at every seam
- Side effects: database writes, cache updates, event emissions are verifiable
- Async resolution: promise resolves with correct value
- Async rejection: promise rejects with correct error; unhandled paths covered

## Key patterns

### Contract — happy path
```js
expect(add(2, 3)).toBe(5);
expect(formatDate('2024-01-15')).toBe('Jan 15, 2024');
```

### Edge / boundary
```js
expect(divide(5, 0)).toThrow('Division by zero');
expect(paginate([], 1, 10)).toEqual({ items: [], total: 0 });
expect(clamp(150, 0, 100)).toBe(100);
```

### Error type & message
```js
expect(() => parseConfig(null)).toThrow(TypeError);
expect(() => parseConfig(null)).toThrow(/required/i);
```

### Pure function — determinism
```js
const result1 = transform(input);
const result2 = transform(input);
expect(result1).toEqual(result2);
```

### Integration — real collaborators
```js
const repo = new UserRepository(testDb);
const service = new UserService(repo);
const user = await service.createUser({ name: 'Alice' });
expect(await repo.findById(user.id)).toMatchObject({ name: 'Alice' });
```

### Side effects verified
```js
await notificationService.send(userId, message);
expect(mockEmailClient.calls).toHaveLength(1);
expect(mockEmailClient.calls[0].to).toBe(userEmail);
```

### Async rejection
```js
await expect(fetchProfile(-1)).rejects.toThrow('Not found');
```

## Common gaps
- Testing only the happy path; skipping `null` / `undefined` arguments
- Asserting a function "doesn't throw" without checking the return value
- Mocking every dependency in an integration test, making it a unit test in disguise
- Not verifying that side effects did NOT fire when they shouldn't have
- Omitting rejection tests for async functions
- Using `toBeTruthy` instead of a precise matcher, hiding partial-match bugs
- Not resetting shared state (module-level caches, singletons) between test cases
