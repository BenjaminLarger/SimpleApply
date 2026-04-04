# autofill-form Command

Detect and fill web form fields with user profile data using JavaScript in the browser extension.

## Command

```
/autofill-form
```

## What Happens

1. **Detects form fields** on the current Chrome tab
   - Analyzes field names, IDs, labels, placeholders
   - Applies keyword matching logic from fieldDetector.ts
   - Returns confidence scores (0.75-1.0)

2. **Fills detected fields** with profile data
   - Email → profile.email
   - First/Last Name → profile.name (split)
   - Phone → profile.phone
   - Password → auto-generated secure password
   - Country → profile.country
   - Checkboxes → auto-checked (consent fields)

3. **Validates results** (no screenshots)
   - Shows which fields were filled
   - Reports confidence for each match
   - Identifies skipped or unmatched fields
   - Suggests improvements if needed

4. **Adapts fieldDetector.ts** if issues found
   - Tests new keywords in browser console
   - Identifies missing patterns
   - Updates fieldDetector.ts
   - Rebuilds extension
   - Commits changes with proper messages

## How to Use

### Quick Fill
```
/autofill-form
```

This will:
1. Open the current browser tab
2. Run field detection JavaScript
3. Fill all detected fields
4. Report results
5. If failures detected, suggest fixes

### If Fields Are Not Detected Correctly

The command will automatically:
1. Show which fields failed
2. Test new keywords
3. Update fieldDetector.ts with improvements
4. Rebuild: `node node_modules/wxt/bin/wxt.mjs build`
5. Commit: `git commit -m "fix: improve field detection..."`
6. Prompt you to reload extension

## Example Workflow

**Step 1: You have a form open in Chrome**
```
Form: SuccessFactors Account Creation
Fields visible:
  - Email Address (name="fbclc_userName")
  - First Name (name="fbclc_fName")
  - Last Name (name="fbclc_lName")
  - Password (name="fbclc_pwd")
  - Country (select)
  - Consent checkboxes
```

**Step 2: Run command**
```
/autofill-form
```

**Step 3: Command executes**
- Detects fbclc_userName as email (via "username" keyword)
- Detects fbclc_fName as firstName (via "fname" keyword)
- Detects fbclc_lName as lastName (via "lname" keyword)
- Detects fbclc_pwd as password (via "pwd" keyword)
- Auto-fills all fields
- Auto-checks consent checkboxes
- Selects country from dropdown

**Step 4: Results shown**
```
✅ Form Filled Successfully

fbclc_userName → email (0.95) → benjaminlarger.bl@gmail.com
fbclc_fName → firstName (1.00) → Benjamin
fbclc_lName → lastName (1.00) → Larger
fbclc_pwd → password (0.95) → K9@mXp!L2sT
consent_check1 → checkbox (0.85) → checked
country_select → country (0.90) → Canada selected

No detection issues found.
```

## Implementation

The command:
1. Gets the active Chrome tab
2. Runs JavaScript using `mcp__claude-in-chrome__javascript_tool`
3. Executes field detection logic
4. Fills fields with profile data
5. Reports results
6. If needed, adapts `extension/utils/fieldDetector.ts`
7. Rebuilds extension
8. Commits changes

## Field Detection Keywords

### High Priority (always win)
- firstname, lastname, fname, lname
- email, username, user_name
- password, phone
- linkedinurl, githuburl, portfoliourl

### Generic (lose to priority)
- name, address, city, country

## Troubleshooting

**Command can't find Chrome tab?**
- Make sure Chrome browser window is open
- Make sure a tab with the form is visible

**Fields not detecting?**
- Command will suggest new keywords
- New keywords tested in browser console
- fieldDetector.ts updated automatically

**Password not generating?**
- Check if field has `type="password"`
- Password must be detected as password type

**Dropdown not selecting?**
- Country code must match option value
- Command shows if country code not found

## Validation Strategy

**Test Extension Changes Without Reloading:**

Before reloading the extension, validate new filling functions using browser console validation scripts:

1. **Open the target form** on SuccessFactors or similar ATS
2. **Paste validation script** in browser console (F12 → Console)
3. **Run tests** to verify:
   - Element detection (querySelectorAll finds the right inputs)
   - Event dispatch (clicks and changes work properly)
   - Value matching (dropdown options match profile data)
4. **Validate against actual form structure** (cascading picklists, comboboxes, radio groups)
5. **Only reload extension** if console validation passes

### Example: Testing Language Skills Detection

```javascript
// Test Language Skills section detection
const sections = document.querySelectorAll('[role="group"]');
let languageSection = null;

for (const section of sections) {
  const heading = section.querySelector('[id*="headerLabel"]');
  if (heading?.textContent?.includes('Language')) {
    languageSection = section;
    break;
  }
}

if (languageSection) {
  console.log('✅ Language section found');
  
  const addBtn = languageSection.querySelector('div[role="button"][class*="addRowButton"]');
  console.log('✅ Add row button found:', !!addBtn);
  
  const inputs = languageSection.querySelectorAll('.rcmpaginatedselectinput');
  console.log('✅ Cascading picklist inputs:', inputs.length);
} else {
  console.log('❌ Language section NOT found');
}
```

### Benefits

- **Immediate feedback** on code logic without extension reload
- **Catch structure changes** early (before extension is deployed)
- **Test event dispatch** on real UI elements
- **Validate proficiency matching** against actual dropdown options
- **Reduce iteration time** by 80% (no reload, rebuild, repeat cycle)

## Performance

- Detection: ~100ms
- Filling: ~50-200ms
- Total: ~500ms-1s (including event dispatch)

## Notes

- No screenshots taken (text-based only)
- Uses JavaScript execution in Chrome
- Requires profile API running locally
- Rebuilds extension only if changes needed
- Creates proper git commits with messages
