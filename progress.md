# simpleApply — Browser Auto-Fill Extension: Progress

## Summary

| Metric | Value |
|--------|-------|
| Total features | 22 |
| Completed | 0 |
| Remaining | 22 |
| Next feature | F001 — FastAPI server (src/api_server.py) |

## How to resume a session

1. Read `features.json` to find the first feature where `"passes": false`.
2. Implement it following its `verification` steps exactly.
3. Run every verification command. If all pass, set `"passes": true` in `features.json` and update the Summary table above.
4. Commit: `git commit -m "feat(extension): <short description> [F00X]"`

## Completed Features

None yet.

## In-Progress / Blockers

None recorded.

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
