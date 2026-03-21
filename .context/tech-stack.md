# Browser Extension Tech Stack

> Research date: 2026-03-20
> Context: Adding a browser extension to simpleApply that auto-detects and fills job application forms, fetching user profile data from a local FastAPI server.

---

## Selected Stack

| Layer | Technology | Version |
|---|---|---|
| Extension framework | WXT | latest |
| Build tooling | Vite (managed by WXT) | via WXT |
| UI (popup + floating banner) | Svelte 5 | latest |
| Language | TypeScript | latest |
| Cross-browser compat | WXT's bundled webextension-polyfill | via WXT |
| Form field detection | Custom classifier | bespoke |
| Shadow DOM traversal | Custom 20-line utility | bespoke |
| Local API client | Native `fetch` + `host_permissions` | MV3 native |
| Unit testing | Vitest + jsdom + @testing-library/jest-dom | latest |
| E2E testing | Playwright (already installed in simpleApply) | reuse existing |

---

## Framework: WXT

- **GitHub**: https://github.com/wxt-dev/wxt — 9,423 stars, last pushed 2026-03-19
- MV3-native with file-based entrypoints (no manual manifest wiring)
- Vite-powered HMR that reloads content scripts on save
- First-party Svelte module: `@wxt-dev/module-svelte`
- Bundles `webextension-polyfill` automatically
- 207 open issues vs Plasmo's 370 — more maintainable for a solo developer

**Why not Plasmo**: Its opinionated content script shadow DOM injection model conflicts with the need to directly manipulate host page DOM. 12,935 stars but 370 open issues.

**Why not CRXJS**: A Vite plugin, not a framework — requires manual wiring of everything WXT provides for free.

---

## UI: Svelte 5

- **GitHub**: https://github.com/sveltejs/svelte — 86,110 stars
- Compiles completely away at build time — zero runtime loaded into host pages
- No conflict with React/Vue already running on LinkedIn, Greenhouse, Lever
- WXT first-party integration via `@wxt-dev/module-svelte`

**Why not Preact**: LinkedIn, Greenhouse, and Lever all use React internally. Injecting Preact creates a second VDOM runtime with risk of event system conflicts. Preact's 3kB runtime is still non-zero.

**Floating banner isolation**: Wrap the injected banner in `element.attachShadow({ mode: 'open' })` so host page CSS cannot bleed into extension UI.

---

## Form Field Detection: Custom Classifier

No maintained library exists for semantic form field classification. Build a scoring function (~150 lines) that examines per-field attributes and returns a profile key or `null`.

**Attributes scored** (in priority order):
1. `autocomplete` — most reliable when present (e.g. `"given-name"`, `"email"`, `"organization"`)
2. `name` — e.g. `"firstName"`, `"linkedin_url"`
3. `id`
4. `aria-label`
5. Adjacent `<label>` text
6. `placeholder`

**Profile key → pattern lookup table** (multilingual, covers EN/FR/ES):

| Profile key | Example patterns |
|---|---|
| `personal_info.name` | `full.?name`, `nom`, `nombre`, `fullname` |
| `personal_info.email` | `email`, `e-mail`, `courriel` |
| `urls.linkedin` | `linkedin` |
| `urls.github` | `github` |
| `urls.portfolio` | `portfolio`, `website`, `site` |
| `education[0].degree` | `degree`, `diploma`, `diplome`, `titre` |
| `experiences[0].company` | `current.?employer`, `company`, `entreprise` |
| `experiences[0].role` | `current.?title`, `job.?title`, `position`, `poste` |

---

## Shadow DOM Traversal (Workday)

Workday wraps forms in deeply nested custom elements with shadow roots. Native `querySelector` cannot reach inside them.

**Utility function** (~20 lines, no library):

```typescript
function queryShadowAll(root: Element | Document, selector: string): Element[] {
  const results: Element[] = [];
  const walk = (node: Element | Document | ShadowRoot) => {
    if (node instanceof Element && node.matches(selector)) results.push(node);
    node.querySelectorAll('*').forEach(child => {
      if (child.shadowRoot) walk(child.shadowRoot);
    });
  };
  walk(root);
  return results;
}
```

> Note: Add a `maxDepth` guard for performance on large Workday pages — `querySelectorAll('*')` on a deep DOM can be slow.

---

## Local API Integration

The FastAPI server (`localhost:8765`) serves profile data to the extension.

- Declare `"http://localhost:8765/*"` in `manifest.json` under `host_permissions`
- Use native `fetch` in content scripts and background service worker
- **CORS**: FastAPI must allow `chrome-extension://<extension-id>` origin
- **Fixed extension ID**: Set a `key` field in `manifest.json` so the extension ID stays stable in developer mode (otherwise it changes on each reload, breaking CORS allowlist)

---

## Dynamic Form Filling (Multi-Entry)

For filling multiple experiences/education entries via "Add" buttons:

```
for each entry in profile.experiences:
  1. Find "Add experience" button → click it
  2. Await MutationObserver fires (new section inserted into DOM)
  3. Detect + fill fields in new section only
  4. Repeat
```

**Platform button selectors** (to be maintained per platform):

| Platform | Button identification strategy |
|---|---|
| Greenhouse | `<button>` text match: "Add another position" |
| LinkedIn Easy Apply | `aria-label` match: "Add another position" |
| Lever | CSS class + text heuristic |
| Workday | `data-automation-id` attribute + shadow DOM traversal |

---

## Testing Strategy

### Unit Tests — Vitest + jsdom
- Test field classifier scoring function
- Test shadow DOM walker with nested jsdom trees
- Test `fillSequence()` async orchestrator (MutationObserver supported in jsdom)
- WXT uses Vitest internally — natural fit

### E2E Tests — Playwright
- Already installed in simpleApply for PDF generation — zero new dependency
- Load unpacked WXT `dist/` via `chromium.launchPersistentContext({ args: ['--load-extension=./dist'] })`
- Test against local HTML fixtures mimicking Greenhouse, Lever, and a Workday-style shadow DOM form
- Location: `tests/extension/`

---

## Supported Platforms (Priority Order)

1. **LinkedIn Easy Apply** — iframe-heavy, React
2. **Greenhouse** (`boards.greenhouse.io`) — standard HTML + React
3. **Lever** (`jobs.lever.co`) — standard HTML
4. **Workday** — shadow DOM, hardest — treat as separate milestone
5. **SmartRecruiters** — standard HTML
6. **Generic HTML forms** — catch-all fallback

---

## Extension Directory Structure

```
extension/
├── wxt.config.ts
├── package.json
├── tsconfig.json
├── entrypoints/
│   ├── background.ts          # service worker, profile fetch + cache
│   ├── content.ts             # injected into all pages, orchestrates filling
│   └── popup/
│       ├── index.html
│       └── App.svelte         # extension toolbar popup
├── components/
│   └── Banner.svelte          # floating auto-fill prompt banner
├── lib/
│   ├── field-detector.ts      # field classifier (~150 lines)
│   ├── shadow-dom.ts          # queryShadowAll utility
│   ├── fill-sequence.ts       # async click→observe→fill orchestrator
│   └── profile-client.ts     # fetch wrapper for localhost:8765
└── tests/
    ├── field-detector.test.ts
    ├── shadow-dom.test.ts
    └── fill-sequence.test.ts
```

---

## Key References

| Resource | URL |
|---|---|
| WXT GitHub | https://github.com/wxt-dev/wxt |
| WXT Svelte module | https://github.com/wxt-dev/wxt/tree/main/packages/module-svelte |
| Svelte GitHub | https://github.com/sveltejs/svelte |
| Vitest GitHub | https://github.com/vitest-dev/vitest |
| Playwright GitHub | https://github.com/microsoft/playwright |
| webextension-polyfill | https://github.com/mozilla/webextension-polyfill |
