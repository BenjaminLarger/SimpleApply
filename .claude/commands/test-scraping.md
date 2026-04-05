# Test Extension Scraping

Automatically test the browser extension's field detection and form filling against HTML snapshots using Playwright MCP.

## Arguments

- `$ARGUMENTS` — Optional: a URL to capture a new snapshot from, OR an ATS name (greenhouse, lever, workday, linkedin, generic) to test existing fixtures. If empty, test ALL existing fixtures.

## Workflow

### Step 1 — Determine test targets

If `$ARGUMENTS` is a URL (starts with http):
1. Use `mcp__playwright__browser_navigate` to open the URL
2. Wait for the page to load fully with `mcp__playwright__browser_wait_for` (wait for `networkidle`)
3. Extract the full page HTML using `mcp__playwright__browser_evaluate` with `document.documentElement.outerHTML`
4. Determine the ATS type from the URL (greenhouse.io → greenhouse, lever.co → lever, myworkdayjobs.com → workday, linkedin.com → linkedin, otherwise → generic)
5. Save the HTML to `extension/tests/e2e/fixtures/{ats-type}-snapshot-{timestamp}.html`
6. Take a screenshot with `mcp__playwright__browser_take_screenshot` for reference
7. Close the browser with `mcp__playwright__browser_close`
8. Proceed to test that snapshot

If `$ARGUMENTS` is an ATS name:
- Find matching fixtures in `extension/tests/e2e/fixtures/` using Glob for `*{ats-name}*`

If `$ARGUMENTS` is empty:
- Test ALL `.html` files in `extension/tests/e2e/fixtures/`

### Step 2 — Read the actual source code

Read these files to get the REAL detection and filling logic (do NOT use hardcoded copies):
- `extension/utils/fieldDetector.ts` — the `detectFields()` function and all keyword maps
- `extension/utils/dynamicFiller.ts` — the `fillForm()` function
- `extension/utils/profile-client.ts` — the `ProfileData` interface
- Check for ATS-specific adapters in `extension/utils/adapters/` that match the target ATS

### Step 3 — Test each fixture with Playwright MCP

For each HTML fixture file:

1. **Navigate** to the fixture:
   ```
   mcp__playwright__browser_navigate → file:///absolute/path/to/fixture.html
   ```

2. **Take a snapshot** to see the page structure:
   ```
   mcp__playwright__browser_snapshot
   ```

3. **Inject the field detection code** by translating the TypeScript source from `fieldDetector.ts` into browser-compatible JavaScript, then inject it:
   ```
   mcp__playwright__browser_evaluate → inject detectFields, FIELD_KEYWORDS, AUTOCOMPLETE_MAP, etc.
   ```
   IMPORTANT: Always translate from the CURRENT source code, never use stale copies.

4. **Run field detection** and collect results:
   ```
   mcp__playwright__browser_evaluate →
     const results = detectFields(document.documentElement);
     return results.map(r => ({
       fieldType: r.fieldType,
       confidence: r.confidence,
       tagName: r.element.tagName,
       id: r.element.id,
       name: r.element.getAttribute('name'),
       placeholder: r.element.getAttribute('placeholder'),
       ariaLabel: r.element.getAttribute('aria-label'),
       autoComplete: r.element.getAttribute('autocomplete'),
     }));
   ```

5. **Evaluate detection quality**:
   - List all detected fields with their types and confidence scores
   - List all input/textarea elements that were NOT detected (missed fields)
   - Flag any misdetections (wrong field type assigned)
   - Check for expected fields based on ATS type:
     - **All ATS**: firstName/fullName, lastName, email (MUST be detected)
     - **Greenhouse**: phone, linkedin, resume_url
     - **Lever**: phone, linkedin, portfolio/website
     - **Workday**: address, city, country, postalCode
     - **LinkedIn**: phone, headline, summary

6. **Test form filling** with a mock profile:
   ```
   mcp__playwright__browser_evaluate →
     const profile = {
       name: 'Test User',
       email: 'test@example.com',
       phone: '+1 555-123-4567',
       linkedin: 'https://linkedin.com/in/testuser',
       github: 'https://github.com/testuser',
       portfolio: 'https://testuser.dev',
       address: '123 Main St',
       city: 'San Francisco',
       postalCode: '94102',
       country: 'United States',
       experiences: []
     };
     // Run fillForm and return filled values
   ```

7. **Verify filled values** by reading back all input values:
   ```
   mcp__playwright__browser_evaluate →
     return Array.from(document.querySelectorAll('input, textarea')).map(el => ({
       id: el.id,
       name: el.getAttribute('name'),
       value: el.value,
       expected: '...' // what we expected to fill
     }));
   ```

### Step 4 — Report results

For each fixture, output a structured report:

```
## Results: {fixture-name}

### Field Detection
| Field Type | Confidence | Element | Status |
|-----------|-----------|---------|--------|
| firstName | 0.95 | #first_name | OK |
| email | 1.00 | #email | OK |

### Missed Fields (inputs not detected)
- <input id="custom_field" name="..." /> — not matched by any keyword

### Form Fill Verification
| Field | Expected | Actual | Status |
|-------|----------|--------|--------|
| #first_name | Test | Test | OK |
| #email | test@example.com | test@example.com | OK |

### Issues Found
1. [MISS] Field #resume_url not detected — consider adding "resume" to keywords
2. [WRONG] Field #company detected as "fullName" — "company" matches "nom" in fullName keywords
```

### Step 5 — Auto-fix (if issues found)

If detection issues are found:
1. Identify the root cause in `fieldDetector.ts` (missing keyword, wrong priority, false positive)
2. Propose the fix (add keyword, adjust confidence, add exclusion)
3. Apply the fix to the source file
4. Re-run the test from Step 3 to verify the fix works
5. Run the existing unit tests to ensure no regressions: `cd extension && npm run test`
6. Repeat until all fixtures pass cleanly or you've exhausted reasonable fixes

### Step 6 — Regression check

After any code changes, run the full test suite:
```bash
cd extension && npm run test
```

Report any regressions introduced by the fixes.

## Key Rules

- NEVER duplicate the detection/filling code in tests — always read from the actual source files
- ALWAYS close the Playwright browser when done (`mcp__playwright__browser_close`)
- When capturing snapshots from live sites, strip any sensitive/personal data before saving
- Keep fixture files under 500KB — strip unnecessary CSS/JS assets from captured HTML
- If a live site requires login or has anti-bot protection, report it and skip rather than trying to bypass
