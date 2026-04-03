# Children's App QA Reference

Use this reference when testing apps designed for children (ages 4–12). The stakes are different: bugs aren't just annoyances — they block learning, erode trust with parents, and can strand a child in an unusable state.

## Core principles

1. **Never block the child** — no interaction should lock up with no way out
2. **Preserve progress** — data loss is a serious failure mode (parents see it, children cry)
3. **Keep dev tools invisible** — skip buttons and admin shortcuts must never be reachable by accident
4. **Simple is correct** — if an 8-year-old can't figure it out in 3 seconds, it's a UX bug

---

## Test areas

### Never-Block Interactions
```typescript
// Any timed interaction must have a hard exit after N failures
it('moves to the next word after 3 failed mic attempts', () => {
  // fire 3 recognition errors
  // assert: next word shown, not stuck on the same one
});

// No confirm() dialogs — they're scary and confusing for children
it('uses modal state, not confirm(), for destructive actions', () => {
  expect(document.querySelector('[data-testid="confirm-modal"]')).not.toBeNull();
  // or check there's no confirm() call in source:
  // grep -r "confirm(" src/ should return nothing
});
```

### Touch Target Size
Minimum 44×44px per Apple/Google accessibility guidelines. On a phone, a 20px button is nearly impossible for small fingers:

```typescript
it('all interactive elements have at least 44x44px touch target', () => {
  const buttons = document.querySelectorAll('button, [role="button"], a');
  buttons.forEach(btn => {
    const { width, height } = btn.getBoundingClientRect();
    expect(Math.max(width, 44)).toBeGreaterThanOrEqual(44);
    expect(Math.max(height, 44)).toBeGreaterThanOrEqual(44);
  });
});
```

### Text Size
Text below 12px is hard for children to read. 10px is acceptable for very minor labels:

```typescript
it('no body text is smaller than 10px', () => {
  // scan computed styles on text nodes
});
```

### Dev-Mode Safety
Skip buttons, admin tools, and cheat codes must not be reachable by normal play:

```typescript
it('DevPanel is hidden from normal users', () => {
  // Either: only rendered in non-production builds
  process.env.NODE_ENV = 'production';
  render(<App />);
  expect(screen.queryByTitle('DEV')).toBeNull();
  // Or: requires a specific key combo to unlock
});

it('clicking bottom-left corner during gameplay does not trigger DevPanel for anonymous users', () => {
  // Simulate accidental touch in bottom-left
});
```

### Progress Preservation
Verify the app recovers gracefully from all failure modes without wiping progress:

```typescript
it('app starts normally when localStorage has old/partial state', () => {
  localStorage.setItem('app-state', JSON.stringify({ xp: 500 })); // partial
  render(<App />);
  expect(screen.queryByText('Error')).toBeNull(); // no crash
  // XP should be visible, not reset to 0
});
```

### No `<form>` Submits That Reload Page
Forms with `type="submit"` reload the page in some browsers, losing state. Use `onClick` handlers:

```typescript
it('no form elements that could trigger a page reload', () => {
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    expect(form.onsubmit).toBeDefined(); // has preventDefault
    // or check: no submit buttons inside forms
  });
});
```

### Recovery / Exit Path
Every screen must have a way back. A child who gets lost in a broken state has no way to call for help:

```typescript
it('every game screen has an exit button', () => {
  // render each game component
  // assert: back/exit button is present and calls onExit
});
```

---

## Content checks (manual + automated)

- No adult, scary, or violent content in word lists or emojis
- Error messages are encouraging, not alarming ("Oops, try again! 😊" not "Error: invalid input")
- All language appropriate for the target age group
- If the app is multilingual, verify the correct language is shown (RTL for Hebrew/Arabic, etc.)

---

## RTL / Hebrew-specific checks

```typescript
it('all main containers have direction: rtl', () => {
  // check computed direction on root containers
});

it('Hebrew strings with ! have the ! at the end, not the beginning', () => {
  // scan string constants: /^![\u0590-\u05FF]/ should match nothing
  // correct: "נכון! 🎉"   wrong: "!נכון 🎉"
});

it('Hebrew transliterations contain nikud characters', () => {
  words.forEach(w => {
    expect(w.tr).toMatch(/[\u05B0-\u05C7]/); // at least one nikud mark
  });
});
```
