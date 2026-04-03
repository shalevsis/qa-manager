# Cross-Platform Compatibility Test Suite

## When to apply
Use when a feature must work across devices, screen sizes, or browsers. Run at breakpoint boundaries and on real or emulated iOS/Android devices before any release.

## What to test
- Layout correct at breakpoints: 320, 375, 768, 1024, 1440, and 2560px viewport widths
- All interactive touch targets are at least 44x44px (WCAG 2.5.5)
- Every hover-only interaction (tooltip, dropdown on hover) has a tap/click equivalent
- iOS Safari: no `BeforeInstallPromptEvent` — install prompt must not render or must gracefully hide
- iOS Safari: viewport height with on-screen keyboard uses `dvh` (not `vh`) to avoid layout shift
- Back-swipe gesture on iOS/Android does not leave the app in a broken state
- Android Chrome vs Firefox: `input[type=date]` native picker differences handled
- Safari missing APIs: `SpeechRecognition` (`webkitSpeechRecognition` prefix), `CSS.registerProperty`, partial `Intl` support
- ES2018+ features (optional chaining, nullish coalescing, `Promise.allSettled`) polyfilled for target browsers
- Retina (2x/3x) displays render sharp images (srcset or SVG, no blurry raster images)
- Split-screen / multi-window (iPad, desktop OS) reflows layout without overflow or element collision

## Key patterns

**Breakpoint layout assertions**
```
for width in [320, 375, 768, 1024, 1440, 2560]:
  setViewport(width, 812)
  assert no horizontal scroll
  assert nav element visible or collapsed per spec
  assert columns === expectedColumns[width]
```

**Touch target size**
```
for el in interactive_elements:
  rect = el.getBoundingClientRect()
  assert rect.width >= 44
  assert rect.height >= 44
```

**iOS vh vs dvh**
```css
/* Incorrect — shrinks when soft keyboard opens */
height: 100vh;

/* Correct — accounts for dynamic viewport */
height: 100dvh;
```

**Safari API guard**
```js
const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition
if (!SR) {
  // Assert: feature hidden or fallback shown, no ReferenceError thrown
}
```

**Retina image check**
```html
<img src="logo.png"
     srcset="logo@2x.png 2x, logo@3x.png 3x"
     alt="Logo" />
<!-- Assert: srcset present on all raster images, or use SVG -->
```

**Split-screen reflow**
```
setViewport(50% of screen width, fullHeight)  // simulate split-screen
assert no overflow-x
assert no overlapping elements (layout collision)
assert primary content still reachable
```

## Common gaps
- Testing only at 375px and 1440px — missing 320px (smallest common phone) and 2560px (wide monitor)
- Touch targets pass on desktop (mouse click area) but fail when measured as rendered touch size on device
- Hover-only dropdowns that open on `mouseenter` with no `click`/`focus` handler — invisible to touch and keyboard users
- `vh` units used in full-screen modals or sticky footers — keyboard overlay on iOS collapses the layout
- iOS install prompt code throws because `BeforeInstallPromptEvent` is undefined — not guarded
- ES2020+ syntax shipped without Babel/SWC transpilation targeting older Android WebView versions
- Retina check done visually only — no automated assertion that `srcset` or vector assets are present
