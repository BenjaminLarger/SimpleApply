# simpleApply — Browser Auto-Fill Extension: Progress

## Summary

| Metric | Value |
|--------|-------|
| Total features | 22 |
| Completed | 22 |
| Remaining | 0 |
| Next feature | — All features complete! |

## How to resume a session

1. Read `features.json` to find the first feature where `"passes": false`.
2. Implement it following its `verification` steps exactly.
3. Run every verification command. If all pass, set `"passes": true` in `features.json` and update the Summary table above.
4. Commit: `git commit -m "feat(extension): <short description> [F00X]"`

## Completed Features

- **F001** — `src/api_server.py`: FastAPI server on port 8765, `/api/health` + `/api/profile` endpoints, CORS for chrome-extension origins, profile flattened to top-level `name`/`email`/`experiences` keys.
- **F002** — `scripts/run_streamlit.sh`: Launches API server in background before Streamlit, PID file at `/tmp/simpleApply_api.pid`, trap cleanup on EXIT/INT/TERM kills API server when script exits.

## Completed Features (cont.)

- **F003–F016, F020–F022** — Extension scaffold, profile client, field detector, shadow DOM, dynamic filler, content script, background service worker, UI components, unit tests, platform adapters — all passing.
- **F017** — `tests/e2e/generic-form.spec.js`: Playwright E2E test for standard job form. 3 tests pass.
- **F018** — `tests/e2e/greenhouse-fixture.spec.js`: Playwright E2E test for Greenhouse-style form. 4 tests pass.
- **F019** — `tests/e2e/lever-fixture.spec.js`: Playwright E2E test for Lever-style form. 5 tests pass.

## In-Progress / Blockers

None. All 22 features complete.

---

## Feature Dependency Map

```
F001 (API server)
  └── F002 (run_streamlit.sh update)

F003 (wxt.config.ts)
  └── F004 (package.json + npm install)
        └── F005 (tsconfig.json)
              └── F006 (profile-client.ts)
              └── F007 (field-detector.ts)
              └── F008 (shadow-dom.ts)
                    └── F009 (dynamic-filler.ts)
                          └── F010 (content.ts)
                          └── F011 (background.ts)
                    └── F022 (workday adapter)
              └── F012 (AutofillBanner.svelte)
              └── F013 (popup App.svelte)
              └── F014 (unit test: field-detector)
              └── F015 (unit test: shadow-dom)
              └── F016 (unit test: dynamic-filler)

F010 + F012 ready
  └── F017 (E2E: generic form)
  └── F018 (E2E: Greenhouse fixture)
  └── F019 (E2E: Lever fixture)

F010 + F020 + F021 + F022 (platform adapters — build last)
```

## Architecture Notes

- Extension lives in `extension/` inside the main project root.
- The extension directory uses `utils/` for library modules (note: the target spec names this `lib/` — the stub files already created use `utils/`, so continue with `utils/`).
- The API server (`src/api_server.py`) must be running locally on port 8765 for the extension to fetch profile data.
- `background.ts` is missing from the scaffold and must be created at `extension/entrypoints/background.ts`.
- `profile-client.ts` is missing from the scaffold and must be created at `extension/utils/profile-client.ts`.
- Platform adapters directory (`extension/utils/adapters/`) does not exist yet — create it as part of F020.
- E2E test fixtures directory (`extension/tests/e2e/`) does not exist yet — create it as part of F017.
