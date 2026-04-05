import type { ProfileData, Experience, Language } from './profile-client.js';
import type { DetectedField, FieldType } from './fieldDetector.js';

const PROFILE_FIELD_MAP: Partial<Record<FieldType, keyof ProfileData>> = {
  email: 'email',
  phone: 'phone',
  linkedinUrl: 'linkedin',
  githubUrl: 'github',
  portfolioUrl: 'portfolio',
  country: 'country',
  state: 'state',
  city: 'city',
  address: 'address',
  postalCode: 'postalCode',
  // password and checkbox types don't map to profile fields
};

function getNamePart(profile: ProfileData, type: FieldType): string {
  const parts = (profile.name ?? '').split(' ');
  if (type === 'firstName') return parts[0] ?? '';
  if (type === 'lastName') return parts.slice(1).join(' ');
  if (type === 'fullName') return profile.name ?? '';
  return '';
}

function fillInput(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  // Use native value setter to trigger React/Vue/Angular onChange
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    el instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype,
    'value'
  )?.set;

  if (nativeInputValueSetter) {
    nativeInputValueSetter.call(el, value);
  } else {
    el.value = value;
  }

  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

function waitForNewNodes(
  parent: Element,
  timeout = 3000
): Promise<MutationRecord[]> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error('MutationObserver timeout'));
    }, timeout);

    const observer = new MutationObserver((records) => {
      clearTimeout(timer);
      observer.disconnect();
      resolve(records);
    });

    observer.observe(parent, { childList: true, subtree: true });
  });
}

function fillDateField(element: any, profile: ProfileData): void {
  // Determine what type of date this should be based on context
  const title = element.getAttribute?.('title') || '';
  const ariaLabel = element.getAttribute?.('aria-label') || '';
  const searchText = (title + ' ' + ariaLabel).toLowerCase();

  // Walk up DOM tree to find section context (employment vs education)
  let sectionContext = '';
  const actualElement = element._actualElement;
  if (actualElement) {
    let parent = actualElement.parentElement;
    while (parent && !sectionContext) {
      const parentText = parent.textContent?.toLowerCase() || '';
      if (parentText.includes('employment') || parentText.includes('experience')) {
        sectionContext = 'employment';
      } else if (parentText.includes('education')) {
        sectionContext = 'education';
      }
      parent = parent.parentElement;
    }
  }

  const fullSearchText = (searchText + ' ' + sectionContext).toLowerCase();
  console.log('[simpleApply:filler] Date field context:', { title, sectionContext, searchText: fullSearchText });

  let dateValue: string | undefined;
  let expIndex = 0;
  let eduIndex = 0;

  if (searchText.includes('from')) {
    // Start date
    if (sectionContext === 'employment') {
      dateValue = profile.experiences?.[expIndex]?.start || '';
    } else if (sectionContext === 'education') {
      dateValue = profile.education?.[eduIndex]?.startYear || '';
    }
  } else if (searchText.includes('end')) {
    // End date
    if (sectionContext === 'employment') {
      dateValue = profile.experiences?.[expIndex]?.end || '';
    } else if (sectionContext === 'education') {
      dateValue = profile.education?.[eduIndex]?.endYear || '';
    }
  }

  if (dateValue) {
    // Format the date to MM/DD/YYYY
    // Handle various formats: YYYY, YYYY-MM, YYYY-MM-DD, MM/DD/YYYY
    let formatted = dateValue;
    if (dateValue.includes('-') && dateValue.length > 4) {
      const [year, month, day] = dateValue.split('-');
      // If only YYYY-MM, assume last day of month
      if (!day) {
        const nextMonth = new Date(parseInt(year), parseInt(month), 1);
        const lastDay = new Date(nextMonth.getTime() - 1).getDate();
        formatted = `${month}/${lastDay}/${year}`;
      } else {
        formatted = `${month}/${day}/${year}`;
      }
    } else if (dateValue.length === 4) {
      // Just a year - assume 01/01/YYYY for start dates, 12/31/YYYY for end dates
      if (searchText.includes('end')) {
        formatted = `12/31/${dateValue}`;
      } else {
        formatted = `01/01/${dateValue}`;
      }
    }

    console.log('[simpleApply:filler] Setting UI5 date:', { original: dateValue, formatted, title, sectionContext });
    // Use the wrapper's setAttribute which handles nested shadow DOM
    element.setAttribute?.('value', formatted);
  } else {
    console.log('[simpleApply:filler] No date value found for context:', { title, searchText, sectionContext });
  }
}

async function fillExperienceSection(
  root: Element,
  profile: ProfileData
): Promise<void> {
  const addButtons = root.querySelectorAll<HTMLButtonElement>(
    'button[aria-label*="Add"], button[data-action*="add"], button.add-experience, button.add-education'
  );

  for (let i = 0; i < addButtons.length && i < (profile.experiences?.length ?? 0); i++) {
    const btn = addButtons[i];
    const exp = profile.experiences[i];
    if (!exp) continue;

    btn.click();

    try {
      await waitForNewNodes(root, 3000);
    } catch {
      // Section may have rendered synchronously — continue anyway
    }

    // Fill company / role fields that appeared after the click
    const companyInput = root.querySelector<HTMLInputElement>(
      'input[name*="company"], input[id*="company"], input[placeholder*="company" i]'
    );
    const roleInput = root.querySelector<HTMLInputElement>(
      'input[name*="title"], input[id*="title"], input[placeholder*="title" i], input[name*="role"], input[id*="role"]'
    );

    if (companyInput) fillInput(companyInput, exp.company);
    if (roleInput) fillInput(roleInput, exp.role);
  }
}

export async function fillForm(
  root: Element,
  profile: ProfileData,
  detectedFields: DetectedField[]
): Promise<void> {
  // Fill static text/textarea fields
  for (const { element, fieldType } of detectedFields) {
    let value: string | undefined;

    if (fieldType === 'firstName' || fieldType === 'lastName' || fieldType === 'fullName') {
      value = getNamePart(profile, fieldType);
    } else if (fieldType === 'password') {
      // Generate secure password for account creation forms
      value = generateSecurePassword();
    } else if (fieldType === 'date') {
      // Handle date fields (especially UI5 date pickers in SuccessFactors)
      console.log('[simpleApply:filler] Processing date field:', element);
      fillDateField(element, profile);
      continue; // Skip normal fillInput for date fields
    } else {
      const key = PROFILE_FIELD_MAP[fieldType];
      if (key) {
        const raw = profile[key];
        value = typeof raw === 'string' ? raw : undefined;
      }
    }

    if (value !== undefined) {
      fillInput(element, value);
    }
  }

  // Fill select dropdowns (country, region, etc.)
  fillSelectFields(root, profile);

  // Check consent/agreement checkboxes
  checkConsentCheckboxes(root);

  // Fill cascading picklists (Successfactors country, state, etc.)
  await fillCascadingPicklists(root, profile);

  // Fill job-specific information fields
  fillJobSpecificInformation(root, profile);

  // Handle dynamic multi-entry sections (experience, education)
  if (profile.experiences?.length) {
    await fillExperienceSection(root, profile);
  }

  // Fill Language Skills section
  if (profile.languages?.length) {
    await fillLanguageSkills(root, profile);
  }
}

/**
 * Fill job-specific information fields (Gender, Resume URL, experience questions, etc.)
 */
function fillJobSpecificInformation(root: Element, profile: ProfileData): void {
  // Find all combobox elements (UI5 dropdowns) in the job-specific section
  const comboboxes = root.querySelectorAll<HTMLElement>('[role="combobox"]');

  comboboxes.forEach((combobox) => {
    const ariaLabel = combobox.getAttribute('aria-label') || '';
    const placeholder = combobox.getAttribute('placeholder') || '';
    const title = combobox.getAttribute('title') || '';
    const combinedLabel = (ariaLabel + ' ' + placeholder + ' ' + title).toLowerCase();

    // Fill Gender dropdown
    if (combinedLabel.includes('gender')) {
      const genderValue = profile.voluntaryDisclosures?.gender;
      if (genderValue) {
        selectComboboxOption(combobox, genderValue);
        console.log('[simpleApply:filler] Gender field filled:', genderValue);
      }
    }

    // Fill "How did you hear about this position?" - skip for now as we don't have this data
    if (combinedLabel.includes('hear about')) {
      console.log('[simpleApply:filler] "How did you hear" field skipped - no profile data available');
    }
  });

  // Fill Resume/CV URL field
  const resumeUrlInput = root.querySelector<HTMLInputElement>(
    'input[aria-label*="Resume"], input[placeholder*="Resume"], input[name*="resume"]'
  );
  if (resumeUrlInput && profile.portfolio) {
    fillInput(resumeUrlInput, profile.portfolio);
    console.log('[simpleApply:filler] Resume/CV URL filled');
  }

  // Fill experience requirement radio groups
  fillExperienceRadioGroups(root, profile);
}

/**
 * Select an option in a UI5 combobox
 */
function selectComboboxOption(combobox: HTMLElement, optionText: string): void {
  // First, click the combobox to open the dropdown
  combobox.click();

  // Wait briefly for options to render and find the matching option
  setTimeout(() => {
    const options = document.querySelectorAll('[role="option"]');
    for (const option of options) {
      if (option.textContent?.toLowerCase().includes(optionText.toLowerCase())) {
        (option as HTMLElement).click();
        console.log('[simpleApply:filler] Selected option:', optionText);
        return;
      }
    }
  }, 100);
}

/**
 * Fill radio groups for experience requirements
 */
function fillExperienceRadioGroups(root: Element, profile: ProfileData): void {
  const radioGroups = root.querySelectorAll<HTMLElement>('[role="radiogroup"]');

  radioGroups.forEach((group) => {
    const groupLabel = group.previousElementSibling?.textContent ||
                      group.parentElement?.querySelector('label')?.textContent || '';
    const groupLabelLower = groupLabel.toLowerCase();

    // Check for 8+ years experience as Data Modeler
    if (groupLabelLower.includes('8+') && groupLabelLower.includes('data modeler')) {
      const yearsOfExp = calculateYearsOfExperience(profile.experiences);
      const shouldSelect = yearsOfExp >= 8;
      selectRadioInGroup(group, shouldSelect ? 'Yes' : 'No');
      console.log(`[simpleApply:filler] Data Modeler experience (8+ years) set to: ${shouldSelect ? 'Yes' : 'No'} (${yearsOfExp} years)`);
    }

    // Check for 5+ years experience in financial services data modeling
    if (groupLabelLower.includes('5+') && groupLabelLower.includes('financial services')) {
      const hasFinancialExp = hasExperienceInFinancialDataModeling(profile.experiences);
      selectRadioInGroup(group, hasFinancialExp ? 'Yes' : 'No');
      console.log(`[simpleApply:filler] Financial services experience set to: ${hasFinancialExp ? 'Yes' : 'No'}`);
    }
  });
}

/**
 * Select a radio button in a radio group
 */
function selectRadioInGroup(group: HTMLElement, option: 'Yes' | 'No'): void {
  const radios = group.querySelectorAll<HTMLInputElement>('input[type="radio"]');
  radios.forEach((radio) => {
    const label = radio.nextElementSibling?.textContent || '';
    if (label.trim() === option) {
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
}

/**
 * Calculate total years of experience from experience entries
 */
function calculateYearsOfExperience(experiences: Experience[] | undefined): number {
  if (!experiences || experiences.length === 0) return 0;

  let totalYears = 0;
  const now = new Date();

  experiences.forEach((exp) => {
    const startYear = exp.start ? parseInt(exp.start.split('-')[0]) : new Date().getFullYear();
    const endYear = exp.end ? parseInt(exp.end.split('-')[0]) : now.getFullYear();
    totalYears += Math.max(0, endYear - startYear);
  });

  return Math.round(totalYears);
}

/**
 * Check if user has experience in data modeling for financial services
 */
function hasExperienceInFinancialDataModeling(experiences: Experience[] | undefined): boolean {
  if (!experiences) return false;

  return experiences.some((exp) => {
    const text = `${exp.company} ${exp.role} ${exp.description || ''}`.toLowerCase();
    const hasDataModeling = text.includes('data model') || text.includes('modeler');
    const hasFinancial = text.includes('financial') || text.includes('banking') ||
                        text.includes('insurance') || text.includes('fsb') ||
                        text.includes('customer') || text.includes('household') ||
                        text.includes('account') || text.includes('interaction');
    return hasDataModeling && hasFinancial;
  });
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
          console.log(`[simpleApply:filler] Cascading picklist "${ariaLabel}" selected: "${optionText}"`);

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
 * Fill select/dropdown fields universally
 */
function fillSelectFields(root: Element, profile: ProfileData): void {
  const selects = root.querySelectorAll<HTMLSelectElement>('select');
  selects.forEach((select) => {
    const label = getSelectLabel(select);
    const ariaLabel = select.getAttribute('aria-label') || '';
    const combinedLabel = (label + ' ' + ariaLabel).toLowerCase();

    // Try to match country-related selects
    if (combinedLabel.includes('country') || combinedLabel.includes('region') || combinedLabel.includes('nation')) {
      const countryCode = findCountryOption(select, profile.country || 'CA');
      if (countryCode) {
        select.value = countryCode;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[simpleApply:filler] Country select filled with code:', countryCode);
      }
    }
  });
}

/**
 * Automatically check consent/agreement checkboxes
 */
function checkConsentCheckboxes(root: Element): void {
  const checkboxes = root.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    const label = getCheckboxLabel(checkbox);
    const name = checkbox.getAttribute('name') || '';
    const combinedLabel = (label + ' ' + name).toLowerCase();

    // Auto-check consent, notification, and agreement checkboxes
    const isConsentType = /consent|agree|accept|notification|subscribe|privacy|terms/i.test(combinedLabel);
    if (isConsentType && !checkbox.checked) {
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
      console.log('[simpleApply:filler] Consent checkbox checked');
    }
  });
}

/**
 * Get label text for a select element
 */
function getSelectLabel(select: HTMLSelectElement): string {
  const aria = select.getAttribute('aria-label') || '';
  if (aria) return aria;

  const id = select.id;
  if (id) {
    const label = select.ownerDocument.querySelector<HTMLLabelElement>(`label[for="${id}"]`);
    if (label) return label.textContent || '';
  }

  const parentLabel = select.closest('label');
  if (parentLabel) return parentLabel.textContent || '';

  // Check for placeholder or name attribute
  return select.getAttribute('name') || select.getAttribute('placeholder') || '';
}

/**
 * Get label text for a checkbox
 */
function getCheckboxLabel(checkbox: HTMLInputElement): string {
  const aria = checkbox.getAttribute('aria-label') || '';
  if (aria) return aria;

  const id = checkbox.id;
  if (id) {
    const label = checkbox.ownerDocument.querySelector<HTMLLabelElement>(`label[for="${id}"]`);
    if (label) return label.textContent || '';
  }

  const parentLabel = checkbox.closest('label');
  if (parentLabel) return parentLabel.textContent || '';

  return checkbox.getAttribute('name') || '';
}

/**
 * Type text into a cascading picklist dropdown (mimics Workday pattern).
 * Approach: click button → wait for input focus → type text → press Enter
 * Adapted from workday.ts typeIntoDropdown function.
 */
async function typeIntoPicklist(button: HTMLElement, text: string): Promise<void> {
  button.click();
  await new Promise(resolve => setTimeout(resolve, 400));

  const activeEl = document.activeElement;
  if (activeEl instanceof HTMLInputElement) {
    // Use native value setter to trigger framework change handlers
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      'value'
    )?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(activeEl, text);
    } else {
      activeEl.value = text;
    }

    activeEl.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 500));

    // Press Enter to confirm selection
    activeEl.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true })
    );
    await new Promise(resolve => setTimeout(resolve, 300));
    return;
  }

  // Fallback: char-by-char keyboard input
  for (const ch of text) {
    document.activeElement?.dispatchEvent(
      new KeyboardEvent('keydown', { key: ch, bubbles: true })
    );
    document.activeElement?.dispatchEvent(
      new KeyboardEvent('keypress', { key: ch, bubbles: true })
    );
    document.activeElement?.dispatchEvent(
      new KeyboardEvent('keyup', { key: ch, bubbles: true })
    );
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  await new Promise(resolve => setTimeout(resolve, 400));
  document.activeElement?.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true })
  );
  await new Promise(resolve => setTimeout(resolve, 200));
}

/**
 * Fill Language Skills section with user's languages
 */
async function fillLanguageSkills(
  root: Element,
  profile: ProfileData
): Promise<void> {
  if (!profile.languages || profile.languages.length === 0) {
    console.log('[simpleApply:filler] No languages in profile, skipping Language Skills section');
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
        console.log('[simpleApply:filler] Language Skills section found via aria-labelledby:', labelText);
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
        console.log('[simpleApply:filler] Language Skills section found via text content');
        break;
      }
    }
  }

  if (!languageSection) {
    console.log('[simpleApply:filler] Language Skills section not found');
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
    console.log('[simpleApply:filler] Add row button not found in Language Skills section');
    return;
  }

  console.log('[simpleApply:filler] Language Skills add button found, starting to add languages');

  // Add and fill a row for each language
  for (let i = 0; i < profile.languages.length; i++) {
    const lang = profile.languages[i];
    console.log(`[simpleApply:filler] Processing language ${i + 1}/${profile.languages.length}: ${lang.language}`);

    // Get the current row count before clicking add
    const rowsBefore = languageSection.querySelectorAll('tr').length;
    console.log(`[simpleApply:filler] Rows before add: ${rowsBefore}`);

    // Click the add button using multiple methods to ensure it works with SAP UI5
    if (addBtn) {
      // Method 1: Try native SAP juic.fire if available (for SAP UI5)
      const onclickAttr = addBtn.getAttribute('onclick');
      if (onclickAttr && (window as any).juic) {
        console.log('[simpleApply:filler] Using SAP juic.fire() method');
        try {
          const match = onclickAttr.match(/juic\.fire\("([^"]+)","([^"]+)"/);
          if (match) {
            (window as any).juic.fire(match[1], match[2], new Event('click'));
          } else {
            addBtn.click();
          }
        } catch (e) {
          console.log('[simpleApply:filler] SAP juic.fire failed, using standard click:', e);
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
    let rowsAfter = languageSection.querySelectorAll('tr').length;
    let waitCount = 0;
    while (rowsAfter <= rowsBefore && waitCount < 5) {
      await new Promise(resolve => setTimeout(resolve, 400));
      rowsAfter = languageSection.querySelectorAll('tr').length;
      waitCount++;
    }

    console.log(`[simpleApply:filler] Rows after add: ${rowsAfter}`);

    // Find all rows in the section
    const rows = languageSection.querySelectorAll('tr');
    if (rows.length === 0 || rows.length <= rowsBefore) {
      console.log('[simpleApply:filler] No new row added, skipping this language');
      continue;
    }

    // Get the last row (newly added)
    const lastRow = rows[rows.length - 1] as HTMLTableRowElement;
    console.log('[simpleApply:filler] Processing new row. Total rows:', rows.length);

    // Find ALL buttons in this row (language and proficiency)
    const allBtns = lastRow.querySelectorAll<HTMLButtonElement>('button');
    console.log('[simpleApply:filler] Found', allBtns.length, 'buttons in the new row');

    // First button should be the language picker
    if (allBtns.length > 0) {
      const languageBtn = allBtns[0];
      console.log(`[simpleApply:filler] Filling language field with: ${lang.language}`);
      await typeIntoPicklist(languageBtn, lang.language);
      await new Promise(resolve => setTimeout(resolve, 800));
    } else {
      console.log('[simpleApply:filler] No buttons found in row');
      continue;
    }

    // Fill proficiency dropdown if available
    if (lang.proficiency && allBtns.length > 1) {
      // Map common proficiency levels to SuccessFactors options: Beginner, Fluent, Intermediate
      const proficiencyMap: Record<string, string> = {
        'native': 'Fluent',
        'fluent': 'Fluent',
        'advanced': 'Fluent',
        'intermediate': 'Intermediate',
        'basic': 'Beginner',
        'beginner': 'Beginner',
      };

      const targetProficiency = proficiencyMap[lang.proficiency.toLowerCase()] || 'Intermediate';

      // Fill remaining buttons (proficiency fields)
      const proficiencyButtons = Array.from(allBtns).slice(1);

      for (const btn of proficiencyButtons) {
        console.log(`[simpleApply:filler] Filling proficiency field: ${targetProficiency}`);
        await typeIntoPicklist(btn, targetProficiency);
        await new Promise(resolve => setTimeout(resolve, 700));
      }
    } else if (lang.proficiency) {
      console.log('[simpleApply:filler] No proficiency buttons found in row (only 1 button detected)');
    }

    // Brief pause before adding next language
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  console.log(`[simpleApply:filler] Language Skills section completed. Added ${profile.languages.length} language(s)`);
}

/**
 * Find matching country option in select
 */
function findCountryOption(select: HTMLSelectElement, countryName: string): string | null {
  const countryMap: Record<string, string> = {
    'Canada': 'CA',
    'United States': 'US',
    'United Kingdom': 'GB',
    'Germany': 'DE',
    'France': 'FR',
    'Spain': 'ES',
    'España': 'ES',
    'Australia': 'AU',
    'India': 'IN',
    'Mexico': 'MX',
    'Brazil': 'BR',
    'Italy': 'IT',
    'Netherlands': 'NL',
    'Belgium': 'BE',
    'Switzerland': 'CH',
    'Austria': 'AT',
    'Sweden': 'SE',
    'Norway': 'NO',
    'Denmark': 'DK',
    'Poland': 'PL',
    'Portugal': 'PT',
  };

  const countryCode = countryMap[countryName];
  if (countryCode && select.querySelector(`option[value="${countryCode}"]`)) {
    return countryCode;
  }

  // Try to find by matching option text
  for (const option of select.options) {
    if (option.textContent?.toLowerCase().includes(countryName.toLowerCase())) {
      return option.value;
    }
  }

  return null;
}

/**
 * Generate a secure password (for account creation forms)
 */
function generateSecurePassword(): string {
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  const numbers = '0123456789';
  const special = '!@#$%^';

  let password = '';
  password += uppercase[Math.floor(Math.random() * uppercase.length)];
  password += lowercase[Math.floor(Math.random() * lowercase.length)];
  password += numbers[Math.floor(Math.random() * numbers.length)];
  password += special[Math.floor(Math.random() * special.length)];

  // Fill to 14 characters
  const allChars = uppercase + lowercase + numbers + special;
  for (let i = password.length; i < 14; i++) {
    password += allChars[Math.floor(Math.random() * allChars.length)];
  }

  // Shuffle
  return password.split('').sort(() => Math.random() - 0.5).join('');
}
