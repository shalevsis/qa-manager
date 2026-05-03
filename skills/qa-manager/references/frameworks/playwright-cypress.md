# Playwright / Cypress Reference

## Playwright

```typescript
import { test, expect } from '@playwright/test'

test('user can log in', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('user@example.com')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL('/dashboard')
})
```

### Selectors (prefer in this order)
```typescript
page.getByRole('button', { name: 'Submit' })   // role
page.getByLabel('Email')                          // label
page.getByText('Welcome')                         // text
page.locator('[data-testid="submit"]')            // test ID
```

### Key assertions
```typescript
await expect(page).toHaveURL('/dashboard')
await expect(locator).toBeVisible() / .toBeHidden()
await expect(locator).toBeEnabled() / .toBeDisabled()
await expect(locator).toContainText('Hello')
await expect(locator).toHaveCount(3)
```

### API mocking
```typescript
await page.route('**/api/users', route =>
  route.fulfill({ status: 200, body: JSON.stringify([{ id: 1 }]) })
)
```

### Running: `npx playwright test`

## Cypress

```typescript
it('logs in', () => {
  cy.visit('/login')
  cy.get('[data-cy="email"]').type('user@example.com')
  cy.get('[data-cy="submit"]').click()
  cy.url().should('include', '/dashboard')
})
```

### Intercept: `cy.intercept('GET', '/api/users', { fixture: 'users.json' })`
### Running: `npx cypress run`
