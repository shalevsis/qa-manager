# UI Bounds & Overflow Suite

## When to apply
Apply to any frontend project with dynamic content, modals, tooltips, dropdowns, fixed/absolute positioned elements, or responsive layouts. Detect with: grep for `position: fixed`, `position: absolute`, `overflow`, `z-index`, `modal`, `tooltip`, `popover`, `dropdown`.

## What to test

- No element renders outside the visible viewport (no horizontal scroll triggered unexpectedly)
- Modal and dialog boxes are fully contained within the viewport on all supported screen sizes
- Tooltips and popovers do not clip at screen edges — they reposition when near a boundary
- Dropdown menus that open near the bottom of the screen flip upward instead of being cut off
- Long text strings do not overflow their container (names, emails, error messages, user-generated content)
- Fixed-position elements (headers, FABs, cookie banners) do not permanently obscure interactive content
- Z-index stacking: no element is visually hidden behind another when it should be in front
- Absolutely positioned children stay within their intended bounding parent (not relative to viewport accidentally)
- Scroll containers have correct overflow settings — content is scrollable, not clipped silently
- On small screens (320px), no element is wider than the viewport (no horizontal overflow)
- Images and media do not expand beyond their container width
- Dynamic content injection (notifications, banners) does not push interactive elements off screen

## Key patterns

**No horizontal overflow at 320px (Playwright)**
```js
it('no horizontal overflow on smallest viewport', async () => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto('/');
  const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
  const viewportWidth = 320;
  expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
});
```

**Modal fully in viewport**
```js
it('modal stays within viewport bounds', async () => {
  await page.click('[data-testid="open-modal"]');
  const modal = page.locator('[role="dialog"]');
  const box = await modal.boundingBox();
  const viewport = page.viewportSize();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
});
```

**Tooltip repositions near screen edge**
```js
it('tooltip does not clip at right edge', async () => {
  // Hover the last item in a list (near right edge)
  await page.hover('[data-testid="last-item"] [data-testid="info-icon"]');
  const tooltip = page.locator('[role="tooltip"]');
  const box = await tooltip.boundingBox();
  const viewport = page.viewportSize();
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
});
```

**Long text does not overflow container**
```js
it('long username does not overflow card', async () => {
  await page.evaluate(() => {
    document.querySelector('[data-testid="username"]').textContent =
      'averylongusernamethatcouldbreakthelayout_0000000000000';
  });
  const card = page.locator('[data-testid="user-card"]');
  const username = page.locator('[data-testid="username"]');
  const cardBox = await card.boundingBox();
  const nameBox = await username.boundingBox();
  expect(nameBox.x + nameBox.width).toBeLessThanOrEqual(cardBox.x + cardBox.width + 1);
});
```

**Fixed header does not obscure content**
```js
it('fixed header does not cover page content', async () => {
  const header = page.locator('header');
  const headerBox = await header.boundingBox();
  const firstContentEl = page.locator('main > *').first();
  const contentBox = await firstContentEl.boundingBox();
  // Content should start below the header bottom edge
  expect(contentBox.y).toBeGreaterThanOrEqual(headerBox.y + headerBox.height - 1);
});
```

**Dropdown flips when near bottom of viewport**
```js
it('dropdown flips upward when anchor is near bottom', async () => {
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.click('[data-testid="bottom-anchor-dropdown"]');
  const menu = page.locator('[data-testid="dropdown-menu"]');
  const menuBox = await menu.boundingBox();
  const viewport = page.viewportSize();
  expect(menuBox.y + menuBox.height).toBeLessThanOrEqual(viewport.height);
});
```

**Image constrained to container**
```js
it('images do not overflow their grid cell', async () => {
  const images = page.locator('[data-testid="gallery"] img');
  const count = await images.count();
  for (let i = 0; i < count; i++) {
    const img = images.nth(i);
    const container = page.locator('[data-testid="gallery"] .cell').nth(i);
    const imgBox = await img.boundingBox();
    const containerBox = await container.boundingBox();
    expect(imgBox.width).toBeLessThanOrEqual(containerBox.width + 1);
  }
});
```

## Common gaps
- Tested only on developer's screen resolution (1440px) — 320px and 375px never checked
- Tooltips tested for content but not position — they render off-screen on the last column
- Modal tested functionally but bounding box never asserted — it renders behind the viewport on short screens
- Long user-generated content not injected into tests — only mock data with short strings used
- Fixed header height changes on scroll but padding-top of content is static — content hidden on scroll
- Z-index conflict between toast notifications and modal backdrop — only caught visually, never automated
- Dropdown opens downward even at bottom of page — cut off, user cannot see options
