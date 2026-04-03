# UI Interaction Testing

Test every user-facing interaction point. Verify users can actually do what the interface promises.

## What to cover for each element

- **Buttons:** Click triggers correct action; disabled when appropriate; loading state during async; re-enables after completion
- **Text inputs:** Valid input accepted; invalid input rejected with error; max length enforced; empty submission handled; special characters safe
- **Forms:** Submission works; validation before submit; errors shown; form resets after success
- **Modals:** Opens on trigger; closes on cancel/backdrop click/Escape; focus trapped
- **Error states:** Errors shown clearly; clear when resolved
- **Loading states:** Spinner shown during async; clears on completion

## Playwright patterns

```typescript
// Button click → result
await page.getByRole('button', { name: 'Submit' }).click()
await expect(page.getByText('Saved')).toBeVisible()

// Input validation
await page.getByLabel('Email').fill('notanemail')
await page.getByRole('button', { name: 'Submit' }).click()
await expect(page.getByText('Invalid email')).toBeVisible()

// Modal open/close
await page.getByRole('button', { name: 'Open' }).click()
await expect(page.getByRole('dialog')).toBeVisible()
await page.keyboard.press('Escape')
await expect(page.getByRole('dialog')).toBeHidden()
```

## React Testing Library

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

test('submit disabled until valid', async () => {
  const user = userEvent.setup()
  render(<ContactForm />)
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  await user.type(screen.getByLabelText('Email'), 'test@example.com')
  expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
})
```

## Common gaps to look for

- Double-click Submit → duplicate submissions?
- Navigate away during async → data lost?
- Async action fails → retry option?
- Different viewport sizes → layout breaks?
