# Accessibility (a11y) Tests

## When to apply
Use for any user-facing UI component, especially interactive controls, modals, forms, and dynamic content regions.

## What to test
- All interactive elements reachable via keyboard Tab in a logical order
- Focus order matches visual / reading order
- Focus is trapped inside modals while open; restored to trigger on close
- Escape key closes modals and dropdowns
- Buttons and links have accessible names (visible text or aria-label)
- Images have meaningful alt text (or alt="" for decorative images)
- Form inputs have associated labels (via `for`/`id` or `aria-labelledby`)
- Color contrast meets WCAG AA: 4.5:1 for normal text, 3:1 for large text
- No information is conveyed by color alone (icons, status indicators have text/shape)
- Dynamic updates announce to screen readers via aria-live regions
- Touch targets are at least 44x44 CSS pixels on mobile

## Key patterns

### Keyboard navigation — all interactive elements reachable
```js
const focusable = within(dialog).getAllByRole('button');
focusable[0].focus();
userEvent.tab();
expect(focusable[1]).toHaveFocus();
```

### Focus trap in modal
```js
openModal();
const modal = screen.getByRole('dialog');
const buttons = within(modal).getAllByRole('button');
buttons[buttons.length - 1].focus();
userEvent.tab(); // should wrap to first element
expect(buttons[0]).toHaveFocus();
```

### Escape closes modal
```js
openModal();
userEvent.keyboard('{Escape}');
expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
expect(triggerButton).toHaveFocus(); // focus restored
```

### Accessible button name
```js
expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
// icon-only button:
expect(closeButton).toHaveAttribute('aria-label');
```

### Image alt text
```js
expect(screen.getByRole('img', { name: /user avatar/i })).toBeInTheDocument();
// decorative:
expect(decorativeImg).toHaveAttribute('alt', '');
```

### Form label association
```js
const input = screen.getByLabelText(/email address/i);
expect(input).toBeInTheDocument();
```

### aria-live announcement
```js
await submitForm();
const region = screen.getByRole('status'); // aria-live="polite"
expect(region).toHaveTextContent(/saved successfully/i);
```

### Automated axe scan (smoke check)
```js
const { container } = render(<PageComponent />);
const results = await axe(container);
expect(results).toHaveNoViolations();
```

## Common gaps
- Testing keyboard access only via Tab, ignoring arrow-key navigation in composites (menus, tabs, radios)
- Not verifying focus is returned to the trigger element when a modal closes
- Skipping aria-live tests for loading states, not just success/error states
- Accepting axe passing as sufficient — axe catches ~30% of issues; manual checks required
- Images tested for presence of alt attribute but not whether the value is meaningful
- No test for color-contrast in dark mode or high-contrast themes
- Touch target size unchecked on mobile breakpoints
- Not testing that status messages are announced without requiring focus (passive announcements)
