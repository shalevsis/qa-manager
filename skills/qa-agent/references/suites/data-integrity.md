# Suite: Data Integrity

## When to apply
Apply when app behavior is driven by a constants or config file (topics, levels, word banks, routes, badges, etc.). Run whenever that file is modified or a new category/item type is added.

---

## What to test

- Every item has all required fields — no missing keys
- No duplicate IDs within a collection
- Item counts match expected values (exactly N items per category)
- Referential integrity — IDs referenced in one collection exist in another
- No empty strings in required text fields
- Numeric values fall within valid ranges (e.g. weights > 0, levels 1–N)
- Arrays that must be non-empty are not empty

---

## Key patterns

**Validate every item against a required-fields schema:**
```js
const REQUIRED_FIELDS = ['id', 'label', 'category', 'weight'];

ITEMS.forEach((item) => {
  REQUIRED_FIELDS.forEach((field) => {
    expect(item[field]).toBeDefined();       // field exists
    expect(item[field]).not.toBeNull();
    if (typeof item[field] === 'string') {
      expect(item[field].trim().length).toBeGreaterThan(0); // not blank
    }
  });
});
```

**No duplicate IDs:**
```js
it('has no duplicate IDs in COLLECTION', () => {
  const ids = ITEMS.map((item) => item.id);
  const unique = new Set(ids);
  expect(unique.size).toBe(ids.length);
});
```

**Count matches expectation per category:**
```js
it('has exactly EXPECTED_COUNT items in CATEGORY_NAME', () => {
  const subset = ITEMS.filter((item) => item.category === CATEGORY_NAME);
  expect(subset.length).toBe(EXPECTED_COUNT);
});
```

**Referential integrity — foreign IDs resolve:**
```js
it('every CHILD item references a valid PARENT id', () => {
  const parentIds = new Set(PARENT_ITEMS.map((p) => p.id));
  CHILD_ITEMS.forEach((child) => {
    expect(parentIds.has(child.parentId)).toBe(true);
  });
});
```

**Numeric ranges:**
```js
it('all weights are positive and within MAX_WEIGHT', () => {
  ITEMS.forEach((item) => {
    expect(item.weight).toBeGreaterThan(0);
    expect(item.weight).toBeLessThanOrEqual(MAX_WEIGHT);
  });
});
```

---

## Common gaps

- Testing only the first few items manually and assuming the rest are fine
- Not checking for whitespace-only strings (`"   "`) — `toBeDefined()` passes, blank content breaks UI
- Forgetting cross-collection referential integrity (e.g. badge references a level ID that was deleted)
- Assuming item count is static — not asserting it, so silent additions/removals go undetected
- Not validating nested arrays (e.g. an item has an `options` array that could be empty)
- Duplicate IDs across categories not caught because dedup check is per-category only
- Enum/string fields not validated against an allowed-values list (typos silently accepted)
