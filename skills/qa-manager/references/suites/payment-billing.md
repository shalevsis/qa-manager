# Payment & Billing Suite

## When to apply
Apply when testing any checkout flow, subscription management, invoicing, or card data entry. Use a payment processor sandbox and mock processor responses for failure paths.

## What to test

- Card numbers pass Luhn validation and match expected length per brand (Visa 16, Amex 15, etc.)
- Expiry dates in the past are rejected; format is enforced as MM/YY
- CVV requires 3 digits for most brands and 4 digits for Amex
- Processor mock responses exercised: success, card declined, insufficient funds, 3DS challenge, network error
- Submitting the payment form twice (double-click, slow network) results in exactly one charge
- Monetary arithmetic produces correct decimal results without floating-point drift
- Currency amounts display with the correct symbol, decimal places, and locale-aware formatting
- Card data is absent from logs, URLs, and any request to your own server (tokenization in use)
- HTTPS enforced on all payment pages; downgrade or mixed-content blocked
- Subscription trial end triggers a charge; failed renewal presents a clear user-facing error; cancellation is confirmed before any further processing

## Key patterns

**Luhn check**
```
validCard   = '4111111111111111'   # Visa test number
invalidCard = '4111111111111112'
expect(luhn(validCard)).toBe(true)
expect(luhn(invalidCard)).toBe(false)
```

**Expiry validation**
```
expect(validateExpiry('12/20')).toBe(false)   # past date
expect(validateExpiry('1/27')).toBe(false)    # wrong format
expect(validateExpiry('12/27')).toBe(true)
```

**CVV length by brand**
```
expect(validateCVV('123', 'visa')).toBe(true)
expect(validateCVV('1234', 'visa')).toBe(false)
expect(validateCVV('1234', 'amex')).toBe(true)
expect(validateCVV('123', 'amex')).toBe(false)
```

**Processor mock responses**
```
mockProcessor.respond('card_declined',        { status: 402, code: 'card_declined' })
mockProcessor.respond('insufficient_funds',   { status: 402, code: 'insufficient_funds' })
mockProcessor.respond('3ds_required',         { status: 202, action: '3ds_challenge' })
mockProcessor.respond('network_error',        { throws: NetworkError })
# Assert each produces the correct UI state and no duplicate charge
```

**Idempotency (double-submit)**
```
interceptor.delayNext('/api/pay', 2000)
click(payButton)
click(payButton)   # second click while first is in-flight
await settle()
expect(chargesCreated).toBe(1)
expect(payButton.disabled).toBe(true)   # or spinner shown
```

**Float precision**
```
expect(addMoney(10.10, 0.05)).toBe(10.15)           # not 10.150000000001
expect(addMoney(0.1, 0.2)).toBe(0.30)               # classic JS trap
# Use integer cents internally or a decimal library
```

**Currency display**
```
expect(formatCurrency(1234.5, 'USD', 'en-US')).toBe('$1,234.50')
expect(formatCurrency(1234.5, 'EUR', 'de-DE')).toBe('1.234,50 €')
expect(formatCurrency(1234,   'JPY', 'ja-JP')).toBe('¥1,234')   # no decimals
```

**PCI assertions**
```
# Scan log output after a payment attempt
expect(logOutput).not.toMatch(/\b4[0-9]{12}(?:[0-9]{3})?\b/)   # Visa PAN pattern
expect(logOutput).not.toMatch(/cvv|cvc|cvn/i)
# Confirm tokenization: request body sent to your server contains token, not raw PAN
expect(serverRequest.body.card_number).toBeUndefined()
expect(serverRequest.body.payment_token).toBeDefined()
```

## Common gaps

- Testing only the happy path card number — also test edge-case lengths (13-digit Visa, 19-digit) and all-zero inputs
- Not asserting that the Pay button is disabled immediately on first click, allowing race-condition double-charges
- Skipping the 3DS redirect and resume flow entirely
- Checking currency symbol but not decimal-place rules (JPY, KWD, CLF all differ)
- Assuming Luhn validity implies the card exists — Luhn only checks checksum, not issuer reachability
- Not testing subscription proration or mid-cycle plan changes
- Forgetting to verify that a failed charge doesn't partially update the subscription state in the database
