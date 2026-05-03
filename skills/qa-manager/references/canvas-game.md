# Canvas Game Testing Reference

Use this reference when testing browser games that use `<canvas>` + `requestAnimationFrame` (RAF). The main challenges are: the game loop runs outside React's lifecycle, state lives in mutable refs, and the canvas context has no DOM to query.

## What to cover

### 1. RAF Loop Teardown (memory leak prevention)
This is the most common canvas bug. If `cancelAnimationFrame` isn't called on unmount, the loop runs forever in the background — consuming CPU, holding refs, and causing subtle state bugs if the component re-mounts.

```typescript
it('cancels the animation frame loop on unmount', () => {
  const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(42);
  const cafSpy = vi.spyOn(window, 'cancelAnimationFrame');

  const { unmount } = render(<GameArcade words={words} onComplete={vi.fn()} onExit={vi.fn()} />);
  unmount();

  expect(cafSpy).toHaveBeenCalledWith(42); // the frame ID was cancelled
});
```

### 2. Mocking the Canvas Context
`jsdom` doesn't implement canvas rendering — `getContext('2d')` returns null by default. Mock it:

```typescript
// vitest.setup.ts or top of test file
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  fillStyle: '',
  strokeStyle: '',
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  drawImage: vi.fn(),
  createLinearGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  measureText: vi.fn(() => ({ width: 50 })),
  fillText: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
}));
```

### 3. Game Completion — `onComplete` Called with Correct Values
Don't test the canvas drawing; test the game's business logic through its callbacks:

```typescript
it('calls onComplete when all words are collected', async () => {
  const onComplete = vi.fn();
  const words = [{ en: 'cat', emoji: '🐱' }];
  render(<GameArcade words={words} onComplete={onComplete} onExit={vi.fn()} />);

  // Simulate collecting a word by firing the internal collection logic
  // (exact approach depends on how game exposes its state)
  await vi.advanceTimersByTimeAsync(5000);

  // If all words collected, game should have ended
  // expect(onComplete).toHaveBeenCalledWith(1, 1);
});
```

### 4. Hearts / Lives System
```typescript
it('calls onComplete when hearts reach 0', () => {
  const onComplete = vi.fn();
  render(<GameArcade words={mockWords} onComplete={onComplete} onExit={vi.fn()} />);

  // Simulate losing all hearts
  // assert onComplete fires early with current score
  // assert score does not exceed total
});

it('hearts never go below zero', () => {
  // lose 4 hearts in a 3-heart game
  // assert displayed hearts = 0, not -1
});
```

### 5. Score Bounds
```typescript
it('score never exceeds total word count', () => {
  // collect same word multiple times via any exploit
  // assert score <= words.length
});
```

### 6. Keyboard / Touch Controls
```typescript
it('left arrow key moves player left', () => {
  render(<GameArcade ... />);
  fireEvent.keyDown(window, { key: 'ArrowLeft' });
  // verify player state reflects leftward movement
});

it('touch left button moves player left on mobile', () => {
  render(<GameArcade ... />);
  fireEvent.touchStart(screen.getByTestId('btn-left'));
  // verify player state
});
```

## What NOT to test
- Pixel-perfect rendering (meaningless in jsdom — canvas is mocked)
- Frame timing precision (too flaky)
- Exact collision coordinates (test logic at the boundary unit level instead)

## Architecture tip for testability
Canvas games are hard to unit-test because logic and rendering are entangled. The most testable pattern: keep game state in a plain object (`gameState`) updated by pure functions (`updatePlayer`, `checkCollision`, `spawnWord`), and keep the `draw()` function as a thin renderer that reads from state. Then test the pure functions directly — no canvas mock needed.
