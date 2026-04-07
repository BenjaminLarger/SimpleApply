# autofill-form Command

Autonomously test and improve extension field detection and filling by mirroring code, executing, validating, and iterating until all fields are filled.

## Usage

```
/autofill-form
```

**Prerequisites:**
- Chrome is open with a job application form loaded
- Extension auto-fill has been triggered (popup activated once)
- Form is visible on the page
- No further manual intervention needed - Claude Code handles the entire loop

## What It Does (Fully Autonomous Loop)

1. **Reads extension source code**
   - Extracts `extension/utils/fieldDetector.ts` (field detection logic)
   - Extracts `extension/utils/dynamicFiller.ts` (form filling logic)
   - Extracts data mapping utilities

2. **Creates execution script**
   - Converts TypeScript logic to executable JavaScript
   - Merges detection + filling + validation into one script
   - Structured to return JSON results

3. **Loop (repeats until all fields filled or max retries reached)**
   
   **Iteration:**
   - Execute mirrored code in browser console
   - Detect form fields on page
   - Fill fields using logic from dynamicFiller.ts
   - Validate which fields were actually filled
   - Parse JSON results

   **If all fields filled:**
   - Return success report
   - Commit changes
   - Done

   **If some fields empty:**
   - Analyze why (detection failed? filling failed? selector wrong?)
   - Update `extension/utils/fieldDetector.ts` or `extension/utils/dynamicFiller.ts`
   - Rebuild: `npm run build`
   - Mirror the UPDATED source code
   - Execute updated code in console again (same browser tab)
   - Validate again
   - Repeat

## Example Output

```json
{
  "iteration": 1,
  "status": "fail",
  "timestamp": "2026-04-05T14:23:45Z",
  "execution_log": {
    "fields_detected": 10,
    "fields_filled": 8,
    "fields_empty": 2
  },
  "filled_fields": {
    "firstName": { "value": "Benjamin", "filled": true },
    "lastName": { "value": "Larger", "filled": true },
    "email": { "value": "", "filled": false, "reason": "keyword_not_matched" },
    "phone": { "value": "", "filled": false, "reason": "selector_not_found" }
  },
  "next_action": "update_fieldDetector_and_retry"
}
```

On next iteration (after code update + rebuild):

```json
{
  "iteration": 2,
  "status": "pass",
  "timestamp": "2026-04-05T14:24:01Z",
  "execution_log": {
    "fields_detected": 10,
    "fields_filled": 10,
    "fields_empty": 0
  },
  "filled_fields": {
    "firstName": { "value": "Benjamin", "filled": true },
    "lastName": { "value": "Larger", "filled": true },
    "email": { "value": "benjamin@example.com", "filled": true },
    "phone": { "value": "+1-555-0000", "filled": true }
  },
  "next_action": "commit"
}
```

## How to Use It

**Step 1: Set up form (one-time, manual)**
```
1. Open Chrome browser
2. Navigate to job application form
3. Activate simpleApply extension popup (triggers auto-fill once)
4. Extension fills what it can
5. Form is now ready for testing
```

**Step 2: Run command (fully autonomous from here)**
```
/autofill-form
```

**Step 3: Claude Code loops automatically**
```
Iteration 1:
  - Read fieldDetector.ts, dynamicFiller.ts
  - Create validation script
  - Execute in console
  - Get results: 8 fields filled, 2 empty
  - Analyze: "email" field not detected
  - Update fieldDetector.ts: add "email" keyword
  - Rebuild: npm run build
  → Continue to Iteration 2

Iteration 2:
  - Re-read UPDATED fieldDetector.ts
  - Create validation script
  - Execute in console (same tab, no reload)
  - Get results: 10 fields filled, 0 empty
  - Status: PASS
  - Commit: git commit -m "fix(extension): improve field detection"
  → Done
```

**Step 4: Get report**
- Final JSON showing all fields filled
- Improvement metrics (iterations needed, fields fixed per iteration)
- Automatic commits with proper messages

## Execution Script Template

Claude generates and executes this from extension source:

```javascript
// Mirrored from extension source + validation wrapper
(async () => {
  const result = {
    iteration: 1,
    status: 'fail',
    timestamp: new Date().toISOString(),
    execution_log: { fields_detected: 0, fields_filled: 0, fields_empty: 0 },
    filled_fields: {}
  };

  // === FIELD DETECTION (from fieldDetector.ts) ===
  const FIELD_KEYWORDS = {
    firstName: ['firstname', 'first_name', 'fname', 'f_name', 'givenname'],
    lastName: ['lastname', 'last_name', 'lname', 'l_name', 'surname'],
    email: ['email', 'e-mail', 'emailaddress', 'email_address', 'username'],
    phone: ['phone', 'telephone', 'tel', 'mobile', 'phonenumber'],
    password: ['password', 'passwd', 'pwd', 'pass'],
    // ... more from fieldDetector.ts
  };

  function normalise(text) {
    return text.toLowerCase().replace(/[\s_\-]/g, '');
  }

  function detectFieldType(element) {
    const name = element.name || element.id || element.placeholder || '';
    const normalised = normalise(name);
    let bestMatch = null;
    let bestLen = 0;

    for (const [type, keywords] of Object.entries(FIELD_KEYWORDS)) {
      for (const kw of keywords) {
        const normKw = normalise(kw);
        if (normalised.includes(normKw)) {
          const len = normKw === normalised ? 100 + normKw.length : normKw.length;
          if (len > bestLen) {
            bestMatch = { type, keyword: kw };
            bestLen = len;
          }
        }
      }
    }
    return bestMatch;
  }

  // === FORM FILLING (from dynamicFiller.ts) ===
  const PROFILE_DATA = {
    firstName: 'Benjamin',
    lastName: 'Larger',
    email: 'benjamin@example.com',
    phone: '+1-555-0000',
    // ... more from profile
  };

  function fillField(element, fieldType) {
    const value = PROFILE_DATA[fieldType];
    if (!value) return false;

    if (element.tagName === 'SELECT') {
      element.value = value;
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      element.value = value;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return true;
  }

  // === DETECT AND FILL ===
  const inputs = Array.from(
    document.querySelectorAll('input:not([type="hidden"]), select, textarea')
  );
  result.execution_log.fields_detected = inputs.length;

  for (const el of inputs) {
    const fieldName = el.name || el.id || 'unknown';
    const detection = detectFieldType(el);

    if (detection) {
      const filled = fillField(el, detection.type);
      const currentValue = el.value || '';

      result.filled_fields[fieldName] = {
        detected_type: detection.type,
        value: currentValue,
        filled: currentValue.length > 0,
        reason: filled ? 'filled' : 'fill_failed'
      };

      if (currentValue.length > 0) {
        result.execution_log.fields_filled++;
      } else {
        result.execution_log.fields_empty++;
      }
    } else {
      result.filled_fields[fieldName] = {
        detected_type: null,
        value: '',
        filled: false,
        reason: 'keyword_not_matched'
      };
      result.execution_log.fields_empty++;
    }
  }

  // === VALIDATION ===
  result.status = result.execution_log.fields_empty === 0 ? 'pass' : 'fail';
  result.next_action = result.status === 'pass' ? 'commit' : 'update_and_retry';

  console.log(JSON.stringify(result, null, 2));
  return result;
})();
```

## Autonomous Iteration Logic

When validation shows empty fields, Claude **automatically**:

1. **Analyzes failure JSON**
   - Identifies which fields weren't filled
   - Groups by reason: `keyword_not_matched` vs `selector_not_found` vs `fill_failed`

2. **Updates extension source code**
   - If keyword missing: adds to `FIELD_KEYWORDS` in fieldDetector.ts
   - If selector wrong: improves selector matching logic
   - If fill failed: fixes event dispatch or value assignment in dynamicFiller.ts

3. **Rebuilds extension**
   ```bash
   cd extension && npm run build
   ```

4. **Re-mirrors and re-executes** (NO reload needed)
   - Reads the UPDATED source code
   - Creates new execution script with updated logic
   - Executes in same browser tab
   - Validates again
   - Returns new JSON results

5. **Loops until success**
   - If still failing: repeats steps 1-4
   - If passing: commits and exits

6. **Takes screenshot before commit**
   - Captures current form state showing all filled fields
   - Saves screenshot to validate visual confirmation
   - Screenshot proves extension filled the form correctly
   - Screenshot is reference for future testing

7. **Commits on final pass**
   - Takes screenshot of filled form
   - One commit per round of improvements
   - Message includes which fields were fixed
   - Screenshot proof attached to commit via git notes (optional)

## Example: Full Autonomous Loop

**You run:** `/autofill-form`

**Claude does (no user intervention):**

```
ITERATION 1:
  Read fieldDetector.ts, dynamicFiller.ts
  Create execution script
  Execute in console
  Get JSON: { fields_filled: 8, empty: 2, reason: ["keyword_not_matched"] }
  Identify: email, phone keywords missing
  
  Update extension/utils/fieldDetector.ts:
    - Add email: ['email', 'e-mail', ...]
    - Add phone: ['phone', 'tel', ...]
  
  Rebuild: npm run build
  
ITERATION 2:
  Read UPDATED fieldDetector.ts
  Create new execution script
  Execute in console (same tab, no reload)
  Get JSON: { fields_filled: 10, empty: 0 }
  Status: PASS
  
  Take screenshot: capture filled form state
  Verify screenshot shows all fields populated
  
  Commit: git commit -m "fix(extension): add email/phone keywords to fieldDetector"
  
  Done ✅
```

## Performance

- Source code reading: ~100ms per iteration
- Script generation: ~150ms
- Browser execution: ~100-200ms
- Validation: ~50ms
- Per iteration: < 500ms
- Typical test: 1-3 iterations, total < 2 seconds

## Key Principles

- **Fully autonomous**: No user reloads, no manual console log copying
- **Mirrors real code**: Uses actual fieldDetector.ts and dynamicFiller.ts
- **Executes + validates**: Test filling logic and check results in one pass
- **Auto-iterates**: Updates source → rebuilds → re-executes → validates
- **Structured feedback**: Always JSON, never narrative
- **Fast feedback loop**: Complete test cycle in seconds

## Safety Rules

**CRITICAL: Changes must not break logic for other ATS systems**

When updating `fieldDetector.ts` or `dynamicFiller.ts`:

1. **Scope changes narrowly**
   - Add new detector sources rather than modifying existing ones
   - Use pattern matching (regex) to target specific ATS systems
   - Example: CSOD pattern `actionItem\.(\w+)\.` only matches Cornerstone forms, doesn't affect others

2. **Test specificity before generalizing**
   - A fallback should NOT match unintended forms from other ATS systems
   - If uncertain whether a fallback is safe, use pattern matching instead (zero-risk)
   - Example: Text-content resolution fallback could theoretically misclassify if another ATS happens to have matching keywords → avoid generic fallbacks

3. **Preserve priority ordering**
   - Earlier detectors (autocomplete, aria-label, name, id) run first
   - New detectors are added after, so they won't override existing matching
   - This maintains backward compatibility with all working ATS systems

4. **Validate before committing**
   - Confirm the change only helps the target form
   - If in doubt, restrict to pattern-based matching only
   - Update commit message to note which ATS system is being targeted

5. **Document ATS-specific patterns**
   - Add comments in code explaining which ATS systems the pattern targets
   - Example: `// CSOD/Cornerstone ATS pattern: actionItem.FIELDNAME.idTag-...`
   - Helps future changes understand scope
