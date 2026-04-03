# Jest / Vitest Reference

Jest and Vitest share nearly identical APIs. Differences are noted where relevant.

## Test structure

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('ModuleName', () => {
  it('returns expected value for valid input', () => {
    expect(myFunction(42)).toBe(84)
  })
  it('throws when input is negative', () => {
    expect(() => myFunction(-1)).toThrow('Input must be positive')
  })
})
```

## Common matchers

```typescript
expect(value).toBe(42)                  // strict equality
expect(value).toEqual({ a: 1 })         // deep equality
expect(value).toBeTruthy() / .toBeFalsy()
expect(value).toBeNull() / .toBeUndefined() / .toBeDefined()
expect(value).toBeGreaterThan(0)
expect(str).toContain('substring')
expect(str).toMatch(/regex/)
expect(arr).toHaveLength(3)
expect(obj).toHaveProperty('key', 'value')
expect(() => fn()).toThrow(TypeError)
await expect(promise).resolves.toBe(value)
await expect(promise).rejects.toThrow('error')
```

## Mocking

```typescript
const mockFn = vi.fn().mockReturnValue(42)
const mockFn = vi.fn().mockResolvedValue({ data: 'ok' })
vi.spyOn(object, 'method').mockImplementation(() => 'mocked')
vi.mock('./module', () => ({ default: vi.fn(), namedExport: vi.fn() }))
vi.stubGlobal('fetch', vi.fn())

expect(mockFn).toHaveBeenCalled()
expect(mockFn).toHaveBeenCalledWith('arg')
vi.clearAllMocks()   // in afterEach
```

## Fake timers

```typescript
beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

await vi.advanceTimersByTimeAsync(3000)  // advance 3s, flush promises
vi.runAllTimers()
```

## Running

```bash
npx vitest run --coverage
npx jest --coverage
```
