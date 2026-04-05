/**
 * SuccessFactors Application Adapter
 *
 * Handles SuccessFactors-specific form filling, including:
 * - Professional section (cascading picklists)
 * - Education section (cascading picklists)
 * - Language Skills (Idiomas) section
 * - Spanish locale support
 */

import type { ProfileData } from '../profile-client.js';

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

export function isSuccessFactors(): boolean {
  // Check URL first
  if (/successfactors\.com|successfactors\.eu/i.test(window.location.hostname)) {
    console.log('[simpleApply:sf] isSuccessFactors=true (URL)');
    return true;
  }

  // Check DOM for SuccessFactors-specific elements
  const dom = !![
    '[role="group"][aria-labelledby]', // SF section structure
    'input.rcmpaginatedselectinput', // SF cascading picklist
    '[class*="rcm"]', // SF SAP UI5 components
  ].some(selector => document.querySelector(selector));

  if (dom) {
    console.log('[simpleApply:sf] isSuccessFactors=true (DOM)');
  } else {
    console.log('[simpleApply:sf] isSuccessFactors=false (DOM)');
  }

  return dom;
}

// ---------------------------------------------------------------------------
// SuccessFactors Form Filling
// ---------------------------------------------------------------------------

/**
 * Main entry point for SuccessFactors form filling.
 * Handles Professional, Education, and Language Skills sections.
 */
export async function fillSuccessFactorsForm(
  root: Element,
  profile: ProfileData
): Promise<void> {
  // Fill cascading picklists for Professional section
  if (profile.experiences?.length) {
    console.log('[simpleApply:sf] Filling Professional section');
    await fillCascadingPicklists(root, profile);
  }

  // Fill cascading picklists for Education section
  if (profile.education?.length) {
    console.log('[simpleApply:sf] Filling Education section');
    await fillCascadingPicklists(root, profile);
  }

  // Fill Language Skills section
  if (profile.languages?.length) {
    console.log('[simpleApply:sf] Filling Language Skills section');
    await fillLanguageSkills(root, profile);
  }
}

/**
 * Fill cascading picklist fields (Successfactors combobox dropdowns with pagination)
 */
async function fillCascadingPicklists(root: Element, profile: ProfileData): Promise<void> {
  // Find all cascading picklist inputs (identified by class name)
  const picklistInputs = root.querySelectorAll<HTMLInputElement>('.rcmpaginatedselectinput');

  for (const input of picklistInputs) {
    const ariaLabel = input.getAttribute('aria-label') || '';
    const hiddenInput = input.closest('td')?.querySelector<HTMLInputElement>('input[type="hidden"]');
    const ariaOwns = input.getAttribute('aria-owns') || '';

    const fieldLabel = ariaLabel.toLowerCase();

    // Determine what value to fill based on aria-label
    let valueToFill: string | null = null;

    if (fieldLabel.includes('country') || fieldLabel.includes('país')) {
      valueToFill = profile.country || null;
    } else if (fieldLabel.includes('state') || fieldLabel.includes('province') || fieldLabel.includes('región')) {
      valueToFill = profile.state || null;
    } else if (fieldLabel.includes('city') || fieldLabel.includes('ciudad')) {
      valueToFill = profile.city || null;
    }

    if (!valueToFill) continue;

    // Click the input to open the picklist
    input.click();
    input.focus();

    // Wait for options to appear
    await new Promise(resolve => setTimeout(resolve, 200));

    // Find and click the matching option
    const listId = ariaOwns;
    let listContainer = document.getElementById(listId);
    if (!listContainer) {
      listContainer = input.closest('.fd-input-group')?.querySelector('.rcmpaginatedselect_list') || null;
    }

    if (listContainer) {
      const options = listContainer.querySelectorAll('[role="option"]');
      for (const option of options) {
        const optionText = option.textContent?.trim() || '';
        if (optionText.toLowerCase().includes(valueToFill.toLowerCase())) {
          (option as HTMLElement).click();
          console.log(`[simpleApply:sf] Cascading picklist "${ariaLabel}" selected: "${optionText}"`);

          // Update the hidden input field
          if (hiddenInput) {
            hiddenInput.value = optionText;
            hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
          }

          await new Promise(resolve => setTimeout(resolve, 100));
          break;
        }
      }
    }
  }
}

/**
 * Select a value from a SuccessFactors cascading picklist by clicking the input,
 * waiting for options to load, then clicking the matching option.
 */
async function selectPicklistOption(input: HTMLInputElement, value: string): Promise<boolean> {
  // Close any previously open dropdown by clicking on the document body
  (document.activeElement as HTMLElement)?.blur();
  document.body.click();
  await new Promise(resolve => setTimeout(resolve, 300));

  // Click input to open the picklist dropdown
  input.click();
  input.focus();
  await new Promise(resolve => setTimeout(resolve, 800));

  // Retry loop: options may need time to load via AJAX (especially first time)
  for (let attempt = 0; attempt < 3; attempt++) {
    // Find the options list via aria-owns
    const ariaOwns = input.getAttribute('aria-owns') || '';
    let listContainer: HTMLElement | null = document.getElementById(ariaOwns);
    if (!listContainer) {
      listContainer = input.closest('.rcmpaginatedselect')?.querySelector('.rcmpaginatedselect_list') as HTMLElement | null;
    }
    if (!listContainer) {
      const allLists = document.querySelectorAll('[role="listbox"]');
      for (const list of allLists) {
        if ((list as HTMLElement).offsetParent !== null) {
          listContainer = list as HTMLElement;
          break;
        }
      }
    }

    if (listContainer) {
      const options = listContainer.querySelectorAll('[role="option"]');
      if (options.length === 0 && attempt < 2) {
        await new Promise(resolve => setTimeout(resolve, 500));
        continue;
      }
      console.log(`[simpleApply:sf] Picklist has ${options.length} options, looking for "${value}" (attempt ${attempt + 1})`);
      for (const option of options) {
        const optionText = option.textContent?.trim() || '';
        if (optionText.toLowerCase().includes(value.toLowerCase())) {
          (option as HTMLElement).click();
          console.log(`[simpleApply:sf] Selected option: "${optionText}"`);
          await new Promise(resolve => setTimeout(resolve, 200));
          return true;
        }
      }
      console.log(`[simpleApply:sf] No matching option found for "${value}"`);
      return false;
    }

    // No list container found yet, wait and re-click
    if (attempt < 2) {
      await new Promise(resolve => setTimeout(resolve, 500));
      input.click();
      input.focus();
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  console.log(`[simpleApply:sf] No option list found for picklist after retries`);
  return false;
}

/**
 * Fill Language Skills section with user's languages
 */
async function fillLanguageSkills(
  root: Element,
  profile: ProfileData
): Promise<void> {
  if (!profile.languages || profile.languages.length === 0) {
    console.log('[simpleApply:sf] No languages in profile, skipping Language Skills section');
    return;
  }

  // Find the Language Skills section by looking for aria-labelledby that contains "Language" or "Idioma" (Spanish)
  const allSections = root.querySelectorAll('[role="group"][aria-labelledby]');
  let languageSection: Element | null = null;

  for (const section of allSections) {
    const labelId = section.getAttribute('aria-labelledby');
    if (labelId) {
      const labelEl = document.getElementById(labelId);
      const labelText = labelEl?.textContent || '';
      const lowerText = labelText.toLowerCase();
      // Check for both English "language" and Spanish "idioma"
      if (lowerText.includes('language') || lowerText.includes('idioma')) {
        languageSection = section;
        console.log('[simpleApply:sf] Language Skills section found via aria-labelledby:', labelText);
        break;
      }
    }
  }

  // Fallback: check section text content
  if (!languageSection) {
    for (const section of allSections) {
      const content = section.textContent || '';
      // Check for both English "Language" and Spanish "Idiomas"
      if (content.toLowerCase().includes('language') || content.toLowerCase().includes('idioma')) {
        languageSection = section;
        console.log('[simpleApply:sf] Language Skills section found via text content');
        break;
      }
    }
  }

  if (!languageSection) {
    console.log('[simpleApply:sf] Language Skills section not found');
    return;
  }

  // Find the "Add new row" button - look for the add button within the section
  // Try multiple selectors to handle different HTML structures
  let addBtn = languageSection.querySelector<HTMLElement>(
    'div[class*="addRowButton"]'
  );

  if (!addBtn) {
    // Try finding a button with add-related text or aria-label
    const buttons = languageSection.querySelectorAll<HTMLElement>('button, div[role="button"]');
    for (const btn of buttons) {
      const title = btn.getAttribute('title') || '';
      const ariaLabel = btn.getAttribute('aria-label') || '';
      const text = btn.textContent || '';
      if (
        title.toLowerCase().includes('add') ||
        ariaLabel.toLowerCase().includes('add') ||
        text.toLowerCase().includes('add') ||
        title.toLowerCase().includes('añadir') ||
        ariaLabel.toLowerCase().includes('añadir') ||
        text.toLowerCase().includes('añadir')
      ) {
        addBtn = btn;
        break;
      }
    }
  }

  if (!addBtn) {
    console.log('[simpleApply:sf] Add row button not found in Language Skills section');
    return;
  }

  console.log('[simpleApply:sf] Language Skills add button found, starting to add languages');

  // Add and fill a row for each language
  for (let i = 0; i < profile.languages.length; i++) {
    const lang = profile.languages[i];
    console.log(`[simpleApply:sf] Processing language ${i + 1}/${profile.languages.length}: ${lang.language}`);

    // Get the current row count before clicking add (count divs with class "layoutWrapper row")
    const rowsBefore = languageSection.querySelectorAll('div.layoutWrapper.row').length;
    console.log(`[simpleApply:sf] Rows before add: ${rowsBefore}`);

    // Click the add button using multiple methods to ensure it works with SAP UI5
    if (addBtn) {
      // Method 1: Try native SAP juic.fire if available (for SAP UI5)
      const onclickAttr = addBtn.getAttribute('onclick');
      if (onclickAttr && (window as any).juic) {
        console.log('[simpleApply:sf] Using SAP juic.fire() method');
        try {
          const match = onclickAttr.match(/juic\.fire\("([^"]+)","([^"]+)"/);
          if (match) {
            (window as any).juic.fire(match[1], match[2], new Event('click'));
          } else {
            addBtn.click();
          }
        } catch (e) {
          console.log('[simpleApply:sf] SAP juic.fire failed, using standard click:', e);
          addBtn.click();
        }
      } else {
        // Method 2: Standard click with full event sequence
        addBtn.focus();
        addBtn.click();
        addBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        addBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      }
    }

    await new Promise(resolve => setTimeout(resolve, 800));

    // Wait for new row to render
    let rowsAfter = languageSection.querySelectorAll('div.layoutWrapper.row').length;
    let waitCount = 0;
    while (rowsAfter <= rowsBefore && waitCount < 5) {
      await new Promise(resolve => setTimeout(resolve, 400));
      rowsAfter = languageSection.querySelectorAll('div.layoutWrapper.row').length;
      waitCount++;
    }

    console.log(`[simpleApply:sf] Rows after add: ${rowsAfter}`);

    // Find all rows in the section (using div.layoutWrapper.row)
    const rows = languageSection.querySelectorAll('div.layoutWrapper.row');
    if (rows.length === 0 || rows.length <= rowsBefore) {
      console.log('[simpleApply:sf] No new row added, skipping this language');
      continue;
    }

    // Get the last row (newly added)
    const lastRow = rows[rows.length - 1] as HTMLElement;
    console.log('[simpleApply:sf] Processing new row. Total rows:', rows.length);

    // Find ALL inputs in this row with class "rcmpaginatedselectinput"
    const allInputs = Array.from(lastRow.querySelectorAll<HTMLInputElement>('input.rcmpaginatedselectinput'));
    console.log('[simpleApply:sf] Found', allInputs.length, 'picklist inputs in the new row');

    // Map English language names to Spanish equivalents for Spanish-locale forms
    const languageNameMap: Record<string, string[]> = {
      'french': ['Francés', 'French'],
      'english': ['Inglés', 'English'],
      'spanish': ['Español', 'Spanish'],
      'german': ['Alemán', 'German'],
      'portuguese': ['Portugués', 'Portuguese'],
      'italian': ['Italiano', 'Italian'],
      'chinese': ['Chino', 'Chinese'],
      'japanese': ['Japonés', 'Japanese'],
      'arabic': ['Árabe', 'Arabic'],
      'russian': ['Ruso', 'Russian'],
      'dutch': ['Holandés', 'Dutch'],
      'korean': ['Coreano', 'Korean'],
      'hindi': ['Hindi', 'Hindi'],
    };

    // First input should be the language picker
    if (allInputs.length > 0) {
      // Try Spanish name first, then English name
      const langKey = lang.language.toLowerCase();
      const namesToTry = languageNameMap[langKey] || [lang.language];
      let filled = false;
      for (const name of namesToTry) {
        console.log(`[simpleApply:sf] Trying language name: ${name}`);
        filled = await selectPicklistOption(allInputs[0], name);
        if (filled) break;
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      if (!filled) {
        console.log(`[simpleApply:sf] Could not select language "${lang.language}"`);
      }
      await new Promise(resolve => setTimeout(resolve, 800));
    } else {
      console.log('[simpleApply:sf] No picklist inputs found in row');
      continue;
    }

    // Fill proficiency inputs if available
    if (lang.proficiency && allInputs.length > 1) {
      // Map proficiency levels to both English and Spanish SuccessFactors options
      const proficiencyMap: Record<string, string[]> = {
        'native': ['Fluido', 'Fluent'],
        'fluent': ['Fluido', 'Fluent'],
        'advanced': ['Fluido', 'Fluent'],
        'intermediate': ['Intermedio', 'Intermediate'],
        'basic': ['Principiante', 'Beginner'],
        'beginner': ['Principiante', 'Beginner'],
      };

      const proficiencyOptions = proficiencyMap[lang.proficiency.toLowerCase()] || ['Intermedio', 'Intermediate'];

      // Fill remaining inputs (proficiency fields: Speaking, Reading, Writing)
      const proficiencyInputs = allInputs.slice(1);

      for (let j = 0; j < proficiencyInputs.length; j++) {
        let filled = false;
        for (const profName of proficiencyOptions) {
          console.log(`[simpleApply:sf] Filling proficiency field ${j + 1}: trying "${profName}"`);
          filled = await selectPicklistOption(proficiencyInputs[j], profName);
          if (filled) break;
          await new Promise(resolve => setTimeout(resolve, 200));
        }
        await new Promise(resolve => setTimeout(resolve, 700));
      }
    } else if (lang.proficiency) {
      console.log('[simpleApply:sf] No proficiency inputs found in row (only 1 input detected)');
    }

    // Brief pause before adding next language
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  console.log(`[simpleApply:sf] Language Skills section completed. Added ${profile.languages.length} language(s)`);
}
