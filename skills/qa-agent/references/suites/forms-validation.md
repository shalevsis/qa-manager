# Form Validation Tests

## When to apply
Use whenever a UI component or API endpoint accepts user input that must satisfy field-level or cross-field rules before submission is allowed.

## What to test
- Required fields: empty submission is blocked, error appears per field
- Format validation: email, phone, date, URL patterns rejected when malformed
- Cross-field dependencies: e.g. confirm-password must match password
- Async validation: remote uniqueness check (username, email) triggers and resolves
- Multi-step forms: data entered in earlier steps is preserved when navigating back
- Submit button disabled until the whole form is valid
- Double-submit guard: submitting twice fires the handler exactly once
- Error messages cleared when the user fixes the invalid value
- Form resets to initial state after successful submission

## Key patterns

### Required field
```js
await userEvent.click(submitButton);
expect(screen.getByText(/name is required/i)).toBeInTheDocument();
```

### Format validation — email
```js
await userEvent.type(emailInput, 'not-an-email');
await userEvent.tab(); // trigger blur
expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
```

### Cross-field — confirm password
```js
await userEvent.type(passwordInput, 'Secret1!');
await userEvent.type(confirmInput, 'Different');
await userEvent.click(submitButton);
expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
```

### Async validation
```js
server.use(rest.get('/api/check-username', (req, res, ctx) =>
  res(ctx.json({ available: false }))
));
await userEvent.type(usernameInput, 'takenuser');
await waitFor(() =>
  expect(screen.getByText(/username already taken/i)).toBeInTheDocument()
);
```

### Submit disabled until valid
```js
expect(submitButton).toBeDisabled();
await fillRequiredFields();
expect(submitButton).toBeEnabled();
```

### Double-submit guard
```js
await userEvent.click(submitButton);
await userEvent.click(submitButton);
expect(onSubmit).toHaveBeenCalledTimes(1);
```

### Error cleared on fix
```js
await userEvent.click(submitButton); // triggers error
await userEvent.type(emailInput, 'valid@example.com');
await waitFor(() =>
  expect(screen.queryByText(/invalid email/i)).not.toBeInTheDocument()
);
```

### Reset after success
```js
await submitValidForm();
expect(nameInput).toHaveValue('');
expect(screen.queryByText(/required/i)).not.toBeInTheDocument();
```

## Common gaps
- Not testing blur-triggered validation separately from submit-triggered validation
- Skipping async validation timeout / loading states
- Forgetting cross-field revalidation when only one of the pair changes
- Not asserting the submit handler receives the correctly shaped payload
- Missing test that a previously invalid then corrected field unblocks submission
- Multi-step forms: not verifying step-1 data survives a back-and-forward navigation
- No test that the form is not submitted when JS-side validation is bypassed (API-level)
