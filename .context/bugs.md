# Bug Tracker

## BUG-001: Extension popup shows as small white square / content script crash

**Status:** Fixed
**Severity:** Critical — extension is non-functional
**Component:** Browser Extension (WXT + Svelte 5)
**Date reported:** 2026-03-21
**Date fixed:** 2026-03-21

### Root Causes & Fixes Applied

1. **Svelte 5 API incompatibility:** `new AutofillBanner(...)` invalid in Svelte 5. Fixed by removing Svelte from content script entirely — banner now built with plain DOM inside closed Shadow DOM.

2. **`chrome.alarms` undefined:** Removed all alarms code from `background.ts`.

3. **`vite-plugin-svelte@3` incompatible with Svelte 5:** `@wxt-dev/module-svelte` pins v3. Fixed with npm `overrides` in package.json:
   ```json
   "overrides": { "svelte": "^5.0.0", "@sveltejs/vite-plugin-svelte": "^4.0.4" }
   ```

4. **Duplicate `content_scripts` in manifest:** Removed manual entry from `wxt.config.ts` — WXT auto-generates from entrypoints.

---

## BUG-002: Workday form fields not detected or filled

**Status:** Open
**Severity:** High — core feature non-functional on Workday
**Component:** Browser Extension — content script + Workday adapter
**Date reported:** 2026-03-21

### Description

On Workday job application pages (e.g. `https://workday.wd5.myworkdayjobs.com/en-US/Workday/job/.../apply/applyManually`), the extension detects 0 fields. The popup shows "0 elements detected" and only the "Manual Fill" button is visible. The auto-fill banner never appears.

### Observed Behavior

- `isWorkday()` returns `true` (URL-based detection works)
- `detectFields()` returns 0 results
- `countInputs()` returns 0 at initial detection time
- The "Manual Fill" button is available but filling has not been confirmed working

### Root Causes Identified

1. **Timing issue — React SPA rendering:** Workday is a React SPA. Form fields render asynchronously after the content script runs. The MutationObserver (1.5s debounce, 60s timeout) was added but may not be triggering correctly or `bannerInjected` flag prevents re-detection.

2. **Trusted Types CSP blocks Svelte:** Workday's Content Security Policy blocks `createPolicy('svelte-trusted-html')`. This was fixed by removing Svelte from content script, but the error previously caused the content script to crash entirely, preventing any detection.

3. **Field detection misses Workday's naming conventions:** Workday form inputs use attributes like:
   - `name="legalName--firstName"` (double-dash separator)
   - `data-automation-id="legalNameSection_firstName"`
   - `aria-label="First Name"`
   The `fieldDetector.ts` keyword matching may not parse these correctly (e.g. `legalName--firstName` won't match keyword `firstname` after normalization because `legalname` prefix pollutes the match).

4. **`fillWorkday()` adapter field mapping may be wrong:** The adapter looks for `data-automation-id="firstName"` but actual Workday pages use `data-automation-id="legalNameSection_firstName"` or similar compound IDs.

### Attempted Fixes (partially applied, not yet verified)

| Fix | Status |
|-----|--------|
| Added URL-based `isWorkday()` detection | Applied — works |
| Added MutationObserver with 1.5s debounce, 60s timeout | Applied — not verified |
| Made `GET_FIELD_COUNT` and `MANUAL_FILL` detect fields on demand | Applied — not verified |
| Added `data-automation-id` detection step in `fieldDetector.ts` | Applied — may not match Workday's compound IDs |
| `countInputs()` as fallback count for Workday pages | Applied — not verified |

### Remaining Investigation Needed

- Test whether "Manual Fill" button actually triggers `fillWorkday()` and fills fields
- Check if MutationObserver fires after Workday React renders the form
- Inspect actual Workday field attributes at runtime (DevTools) to verify `data-automation-id` values
- Update `fillWorkday()` field matching regexes to handle Workday's actual attribute patterns (e.g. `legalNameSection_firstName`)
- Consider adding more Workday-specific selectors to `FIELD_KEYWORDS` or the adapter
- Test whether `queryShadowAll` correctly pierces Workday's shadow DOM (if any)

### Environment

- Workday test URL: `https://workday.wd5.myworkdayjobs.com/en-US/Workday/job/.../apply/applyManually`
- WXT 0.19.29, Svelte 5.54.1, vite-plugin-svelte 4.x (via overrides)
- Chrome Manifest V3
