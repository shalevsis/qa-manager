# Suite Index — Detection Signals → Suite Files

Read this file in Phase 1, then scan the project and select only matching suites.
Load suite files from `references/suites/`. Load framework from `references/frameworks/`.

---

## Framework Detection

| Signal | Framework file |
|---|---|
| `jest`, `vitest` in `package.json` devDeps | `frameworks/jest-vitest.md` |
| `pytest`, `pyproject.toml`, `pytest.ini` | `frameworks/pytest.md` |
| `playwright`, `cypress` in deps | `frameworks/playwright-cypress.md` |
| None of the above | `frameworks/language-agnostic.md` |

---

## Suite Detection Table

| Detection Signal (grep/check for this) | Suite file(s) to load |
|---|---|
| Any codebase | `suites/core-unit.md` |
| Any codebase | `suites/policy-tests.md` |
| Any UI code (React/Vue/Angular/HTML) | `suites/ui-interaction.md` |
| `<form>`, `onSubmit`, `yup`/`zod`/`joi` in deps | `suites/forms-validation.md` |
| `react-router`, `vue-router`, `next/navigation`, route definitions | `suites/routing-navigation.md` |
| `jwt`, `useAuth`, `login`, `token`, `/auth/` routes, `cookie` | `suites/auth-session.md` |
| `localStorage`, `sessionStorage` | `suites/localstorage-state.md` |
| `fetch`, `axios`, `requests` (Python), REST endpoints | `suites/rest-api.md` |
| `@apollo/client`, `graphql-request`, `gql\`` | `suites/graphql.md` |
| `WebSocket`, `socket.io`, `useWebSocket` | `suites/websocket-realtime.md` |
| `setInterval` polling, `_poll_loop`, repeated API calls on timer | `suites/continuous-polling.md` |
| `threading.Thread`, background tasks, worker processes | `suites/background-workers.md` |
| `SpeechRecognition`, `speechSynthesis`, voice commands | `suites/speech-voice.md` |
| `<input type="file">`, `multer`, `fs.readFile`, file upload/download | `suites/file-handling.md` |
| `navigator.clipboard`, `draggable`, DnD library | `suites/clipboard-dnd.md` |
| `<canvas>`, `requestAnimationFrame`, game loop | `suites/canvas-game.md` |
| SQL queries, `sqlite3`, `psycopg2`, `SQLAlchemy`, ORM | `suites/db-query-safety.md` |
| Test DB setup, env vars for DB, `pytest` fixtures with DB | `suites/fixture-factory.md` |
| Any UI code | `suites/accessibility.md` |
| API keys, secrets, credentials, `.env` files | `suites/security-scan.md` |
| Constants file (`constants.js`, `data.json`), large config arrays | `suites/data-integrity.md` |
| Storage keys, scoring constants, magic numbers used in logic | `suites/regression-traps.md` |
| Weighted random, sampling, spaced repetition, A/B | `suites/statistical-distribution.md` |
| `try/catch`, error boundaries, `.catch()`, error UI components | `suites/error-handling.md` |
| Large lists, virtualization, debounce/throttle, render-heavy components | `suites/performance.md` |
| `i18next`, `react-intl`, multiple locale files, RTL | `suites/i18n.md` |
| `service-worker`, `manifest.json`, `workbox`, cache APIs | `suites/offline-pwa.md` |
| `Notification`, `firebase/messaging`, toast library | `suites/notifications.md` |
| Search input, filter UI, `useDebounce`, query params for filtering | `suites/search-filter.md` |
| `navigator.permissions`, mic/camera/geo/clipboard permission requests | `suites/permissions.md` |
| Targeting children (ages 4–12), educational app, touch-first UX | `suites/children-app.md` |
| `getUserMedia`, camera capture, `<input accept="image/*">` | `suites/image-capture-ai.md`, `suites/camera-hardware.md` |
| Image compression, EXIF, Sharp, canvas image processing, HEIC | `suites/image-quality-preprocessing.md` |
| `FormData`, multipart upload, upload progress tracking | `suites/image-upload-pipeline.md` |
| AI/vision API calls on image data (OpenAI Vision, Gemini, custom) | `suites/ai-vision-robustness.md` |
| Long-form `SpeechRecognition`, dictation, voice-driven UX | `suites/voice-input-extended.md` |
| History/log storage, trends display, stats dashboard, heuristic scoring | `suites/historical-analysis.md` |
| Targeting multiple browsers/OSes/devices, responsive breakpoints | `suites/cross-platform-compat.md` |
| `visibilitychange`, `AppState`, background/foreground lifecycle | `suites/app-resume.md` |
| Stripe, payment SDK, checkout flow, billing UI | `suites/payment-billing.md` |
| Auth, user input rendered, API keys, cookie-based sessions | `suites/application-security.md` |
| Any app making network requests | `suites/network-conditions.md` |
| `fetch`, `axios`, `requests`, any HTTP client | `suites/http-status-codes.md` |
| SPA/component UI with data fetching, AbortController, cross-origin APIs | `suites/request-lifecycle.md` |
| `EventSource`, `text/event-stream`, `ReadableStream`, streaming AI output | `suites/streaming-sse.md` |
| `Cache-Control`, `ETag`, CDN config, React Query, SWR, service worker cache | `suites/network-caching.md` |
| Production/mobile app, HTTPS, multiple networks, proxy, connection pool | `suites/connection-transport.md` |
| HTTPS, `ssl`, `tls`, `.pem`/`.crt`, cert pinning, internal CA, HSTS | `suites/tls-certificates.md` |
| `while True`, `while (true)`, `for(;;)`, recursive functions, retry loops | `suites/loop-safety.md` |
| Any codebase under active development or post-refactor | `suites/dead-code.md` |
| Modals, tooltips, dropdowns, fixed headers, dynamic content, responsive UI | `suites/ui-bounds.md` |
| `fetch`, `axios`, `setInterval`, `session`, `socket`, uploads, background jobs | `suites/timeout-coverage.md` |
| Multiple users, shared state, concurrent writes, job queues, cache, async ops | `suites/concurrency.md` |

---

## Selection guidelines

- **Default always-on:** `core-unit.md`, `policy-tests.md`, `accessibility.md` (for any UI), `application-security.md` (for any app with auth or user input), `network-conditions.md` (for any app making requests)
- **Load only what matches** — a project with no camera doesn't need `camera-hardware.md`
- **When in doubt, include** — a false positive (loading an irrelevant suite) is better than a false negative (missing a coverage area)
- **Announce your selection** to the user before proceeding
