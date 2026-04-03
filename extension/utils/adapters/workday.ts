/**
 * Workday Application Adapter
 *
 * Mirrors the flow from https://github.com/ubangura/Workday-Application-Automator
 * Adapted from Puppeteer to content-script DOM APIs.
 *
 * Reference repo flow:
 *   signIn → startApp → fillBasicInfo → fillExperience →
 *   fillVoluntaryDisclosures → fillSelfIdentify
 *
 * Each page is filled by targeting elements directly via selectors
 * (data-automation-id first, then name/id fallback), NOT by looping inputs.
 */

import { queryShadowAll } from '../shadowDom.js';
import type { ProfileData } from '../profile-client.js';

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

export function isWorkday(): boolean {
  if (/myworkdayjobs\.com|workday\.com/i.test(window.location.hostname)) {
    console.log('[simpleApply:workday] isWorkday=true (URL)');
    return true;
  }
  const dom = !![
    '[data-automation-id="legalNameSection"]',
    '[data-automation-id="email"]',
    '[class*="wd-"]',
    'workday-web',
  ].find((s) => document.querySelector(s));
  console.log('[simpleApply:workday] isWorkday=', dom, '(DOM)');
  return dom;
}

// ---------------------------------------------------------------------------
// Helpers — mirrors withOptSelector / selectorExists from reference repo
// ---------------------------------------------------------------------------

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Wait for a selector to appear in the DOM (like Puppeteer page.waitForSelector).
 */
function waitForSelector<T extends Element>(
  selector: string,
  timeout = 2000
): Promise<T | null> {
  const el = document.querySelector<T>(selector);
  if (el) return Promise.resolve(el);
  return new Promise((resolve) => {
    const timer = setTimeout(() => { obs.disconnect(); resolve(null); }, timeout);
    const obs = new MutationObserver(() => {
      const found = document.querySelector<T>(selector);
      if (found) { clearTimeout(timer); obs.disconnect(); resolve(found); }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  });
}

/**
 * Like reference repo's selectorExists — returns boolean.
 */
async function selectorExists(selector: string, timeout = 1000): Promise<boolean> {
  return (await waitForSelector(selector, timeout)) !== null;
}

/**
 * Like reference repo's withOptSelector — find element, run callback, swallow miss.
 * Accepts multiple selector candidates (tries in order).
 */
async function withOpt<T extends Element>(
  selectors: string | string[],
  callback: (el: T) => void | Promise<void>,
  timeout = 2000
): Promise<boolean> {
  const list = Array.isArray(selectors) ? selectors : [selectors];
  for (const sel of list) {
    const el = await waitForSelector<T>(sel, timeout);
    if (el) {
      await callback(el);
      return true;
    }
  }
  return false;
}

/**
 * Set a value on an input using the native setter + dispatch events.
 * Equivalent to Puppeteer's el.fill().
 */
function fill(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  el.focus();
  const proto = el instanceof HTMLTextAreaElement
    ? HTMLTextAreaElement.prototype
    : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (setter) setter.call(el, value);
  else el.value = value;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
}

/**
 * Type characters one by one — mirrors Puppeteer's page.keyboard.type(text, {delay}).
 * Needed for Workday React date inputs that ignore bulk value sets.
 */
async function typeChars(el: HTMLInputElement, text: string, charDelay = 100): Promise<void> {
  el.focus();

  // Clear field first to avoid appending to existing values
  const proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  const setter = proto?.set;
  if (setter) setter.call(el, '');
  else el.value = '';
  el.dispatchEvent(new Event('input', { bubbles: true }));

  for (const ch of text) {
    el.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keypress', { key: ch, bubbles: true }));

    // Append character one by one
    const currentValue = el.value;
    if (setter) setter.call(el, currentValue + ch);
    else el.value = currentValue + ch;

    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }));
    await delay(charDelay);
  }
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Map long degree strings to standard Workday dropdown values.
 */
function mapDegreeToWorkday(degree: string): string {
  const d = degree.toLowerCase();
  if (d.includes('master')) return "Master's Degree";
  if (d.includes('bachelor') || d.includes('licence') || d.includes('engineering')) return "Bachelor's Degree";
  if (d.includes('phd') || d.includes('doctor')) return 'Doctorate';
  if (d.includes('associate')) return "Associate's Degree";
  if (d.includes('mba')) return "Master of Business Administration (M.B.A.)";
  if (d.includes('high school') || d.includes('ged')) return 'High School or Equivalent';
  // Return original if no mapping found
  return degree;
}

const RESUME_STORAGE_KEY = 'simpleApply_resume';

/**
 * Inject resume from chrome.storage into a file input via DataTransfer API.
 */
async function injectResume(input: HTMLInputElement): Promise<boolean> {
  const stored = await chrome.storage.local.get(RESUME_STORAGE_KEY);
  const resume = stored[RESUME_STORAGE_KEY];
  if (!resume?.fileData) {
    console.log('[simpleApply:workday] No resume in storage — skipping upload');
    return false;
  }

  const binary = atob(resume.fileData);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

  const file = new File([bytes], resume.fileName ?? 'resume.pdf', {
    type: resume.contentType ?? 'application/pdf',
  });

  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;

  input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
  input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
  await delay(200);
  input.dispatchEvent(new FocusEvent('blur', { bubbles: true }));

  console.log(`[simpleApply:workday] Resume injected: ${resume.fileName} (${bytes.length} bytes)`);
  return input.files.length > 0;
}

/**
 * Check if Workday already has a resume uploaded.
 */
function resumeAlreadyUploaded(): boolean {
  return !!document.querySelector('[data-automation-id="file-upload-item"]')
    || document.body.innerText.includes('Successfully Uploaded');
}

/**
 * Wait for Workday to confirm the upload.
 */
async function waitForUploadConfirmation(timeoutMs = 10_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (document.querySelector('[data-automation-id="file-upload-item"]')) return true;
    await delay(300);
  }
  return false;
}

/** Max skills to enter — avoids 10+ minute fills */
const MAX_SKILLS = 8;

/**
 * Simulate keyboard.type() + Enter on a dropdown/combobox.
 * Mirrors reference repo: el.click() → page.keyboard.type(text) → Enter
 */
async function typeIntoDropdown(
  button: HTMLElement,
  text: string
): Promise<void> {
  button.click();
  await delay(400);

  // After click, Workday focuses a search input inside the popup
  const active = document.activeElement;
  if (active instanceof HTMLInputElement) {
    fill(active, text);
    await delay(500);
    active.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    await delay(300);
    return;
  }

  // Fallback: char-by-char keyboard events (mirrors page.keyboard.type(text, {delay:100}))
  for (const ch of text) {
    for (const type of ['keydown', 'keypress', 'keyup'] as const) {
      document.activeElement?.dispatchEvent(new KeyboardEvent(type, { key: ch, bubbles: true }));
    }
    await delay(100);
  }
  await delay(400);
  document.activeElement?.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true })
  );
  await delay(200);
}

function waitForMutation(root: Element, timeout = 5000): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => { obs.disconnect(); resolve(); }, timeout);
    const obs = new MutationObserver(() => { clearTimeout(timer); obs.disconnect(); resolve(); });
    obs.observe(root, { childList: true, subtree: true });
  });
}

/**
 * Wait until at least `expected` elements match the selector appear in DOM.
 * Uses MutationObserver for DOM-stable waiting instead of flat delay.
 */
async function waitForFormCount(selector: string, expected: number, timeout = 5000): Promise<void> {
  const currentCount = document.querySelectorAll(selector).length;
  console.log(`[simpleApply:workday] [waitForFormCount] Starting wait for selector "${selector}" (current: ${currentCount}, expected: ${expected}, timeout: ${timeout}ms)`);

  if (currentCount >= expected) {
    console.log(`[simpleApply:workday] [waitForFormCount] Already have enough elements, returning immediately`);
    return;
  }

  let mutationFired = false;
  let finalCount = currentCount;

  await new Promise<void>((resolve) => {
    const timer = setTimeout(() => {
      console.log(`[simpleApply:workday] [waitForFormCount] TIMEOUT after ${timeout}ms (mutations: ${mutationFired}, final count: ${finalCount})`);
      obs.disconnect();
      resolve();
    }, timeout);

    const obs = new MutationObserver(() => {
      mutationFired = true;
      finalCount = document.querySelectorAll(selector).length;
      console.log(`[simpleApply:workday] [waitForFormCount] MutationObserver fired - count now: ${finalCount}`);

      if (finalCount >= expected) {
        console.log(`[simpleApply:workday] [waitForFormCount] Target count reached, resolving`);
        clearTimeout(timer);
        obs.disconnect();
        resolve();
      }
    });

    console.log(`[simpleApply:workday] [waitForFormCount] Starting MutationObserver...`);
    obs.observe(document.body, { childList: true, subtree: true });
  });

  const afterCount = document.querySelectorAll(selector).length;
  console.log(`[simpleApply:workday] [waitForFormCount] Wait complete - final count: ${afterCount}`);
}

/**
 * Find a section heading element by matching text from a list of candidates.
 */
function findSectionHeader(textMatches: string[]): Element | null {
  const allHeadings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]'));
  return allHeadings.find(el => {
    const t = el.textContent?.trim().toLowerCase() ?? '';
    return textMatches.some(m => t === m);
  }) ?? null;
}

/**
 * Find and click the Add/Add Another button for a given section.
 * Uses Y-position brackets: button must be BELOW the target section header
 * and ABOVE the next section header (if known).
 */
async function clickAddInSection(sectionSel: string, label: string): Promise<boolean> {
  console.log(`[simpleApply:workday] [clickAddInSection] Looking for: "${label}"`);

  const searchText = label.toLowerCase();
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('button'));
  const addButtons = buttons.filter(b => /^add/i.test(b.textContent?.trim() ?? ''));

  console.log(`[simpleApply:workday] [clickAddInSection] Found ${buttons.length} total buttons, ${addButtons.length} with "add"`);

  // Identify target + boundary headers for Y-bracket scoping
  let targetTexts: string[] = [];
  let boundaryTexts: string[] = [];

  if (searchText.includes('work')) {
    targetTexts  = ['work experience', 'experience'];
    boundaryTexts = ['education', 'education history', 'certifications', 'skills'];
  } else if (searchText.includes('education')) {
    targetTexts  = ['education', 'education history'];
    boundaryTexts = ['certifications', 'skills', 'languages', 'websites', 'references'];
  }

  const targetHeader   = findSectionHeader(targetTexts);
  const boundaryHeader = findSectionHeader(boundaryTexts);

  const targetY   = targetHeader   ? targetHeader.getBoundingClientRect().bottom   : -Infinity;
  const boundaryY = boundaryHeader ? boundaryHeader.getBoundingClientRect().top    :  Infinity;

  console.log(`[simpleApply:workday] [clickAddInSection] "${label}" header Y=${targetY.toFixed(0)}, boundary Y=${boundaryY === Infinity ? '∞' : boundaryY.toFixed(0)}`);

  // Collect candidate buttons in the Y-bracket
  const inRange = addButtons.filter(b => {
    const y = b.getBoundingClientRect().top;
    return y > targetY && y < boundaryY;
  });
  inRange.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

  inRange.forEach(b => console.log(`[simpleApply:workday] [clickAddInSection]   Candidate: "${b.textContent?.trim()}" at Y=${b.getBoundingClientRect().top.toFixed(0)}`));

  let selectedBtn: HTMLButtonElement | null = inRange[0] ?? null;

  // Fallback: if no header found or no in-range button, take first "Add Another" then first "Add"
  if (!selectedBtn) {
    const fallback = addButtons.find(b => b.textContent?.trim().toLowerCase() === 'add another')
                  ?? addButtons.find(b => b.textContent?.trim().toLowerCase() === 'add')
                  ?? null;
    console.warn(`[simpleApply:workday] [clickAddInSection] No in-range button found, fallback: "${fallback?.textContent?.trim()}"`);
    selectedBtn = fallback;
  }

  if (!selectedBtn) {
    console.warn(`[simpleApply:workday] [clickAddInSection] Could not find any suitable button for "${label}"`);
    return false;
  }

  const btnText  = selectedBtn.textContent?.trim() ?? 'unknown';
  const isVisible = selectedBtn.offsetParent !== null;
  console.log(`[simpleApply:workday] [clickAddInSection] Clicking: "${btnText}" at Y=${selectedBtn.getBoundingClientRect().top.toFixed(0)} (visible: ${isVisible})`);
  selectedBtn.click();
  console.log(`[simpleApply:workday] [clickAddInSection] Click executed`);
  return true;
}

// ---------------------------------------------------------------------------
// Next button — mirrors reference repo's nextButton constant
// ---------------------------------------------------------------------------

const NEXT_BTN_SELS = [
  'button[data-automation-id="bottom-navigation-next-button"]',
  'button[data-automation-id="nextButton"]',
  // Fallback: find by visible text content
];

function findNextButton(): HTMLButtonElement | null {
  for (const sel of NEXT_BTN_SELS) {
    const btn = document.querySelector<HTMLButtonElement>(sel);
    if (btn && !btn.disabled) return btn;
  }
  // Fallback: find button by text content "Next" or "Continue"
  const allButtons = document.querySelectorAll<HTMLButtonElement>('button');
  for (const btn of allButtons) {
    const text = btn.textContent?.trim().toLowerCase() ?? '';
    if ((text === 'next' || text === 'continue' || text === 'save and continue')
        && !btn.disabled) {
      return btn;
    }
  }
  return null;
}

async function clickNext(timeout = 5000): Promise<boolean> {
  const btn = findNextButton();
  if (!btn) {
    console.log('[simpleApply:workday] No Next button found');
    return false;
  }
  console.log('[simpleApply:workday] Clicking Next:', btn.textContent?.trim());
  const p = waitForMutation(document.body, timeout);
  btn.click();
  await p;
  return true;
}

// ---------------------------------------------------------------------------
// fillBasicInfo — mirrors reference repo apply.js fillBasicInfo()
// ---------------------------------------------------------------------------

async function fillBasicInfo(profile: ProfileData): Promise<void> {
  console.log('[simpleApply:workday] Filling basic info');

  const nameParts = profile.name.split(' ');
  const firstName = nameParts[0] ?? '';
  const lastName = nameParts.slice(1).join(' ');

  // Previous Worker → click "No" (second radio, id="2" in reference repo)
  // Real DOM: input[name="candidateIsPreviousWorker"], second radio = No
  await withOpt<HTMLInputElement>(
    'div[data-automation-id="previousWorker"] input[id="2"]',
    (el) => el.click(),
    10000
  ).then(async (found) => {
    if (!found) {
      // Fallback: find by name attribute
      const radios = document.querySelectorAll<HTMLInputElement>(
        'input[name="candidateIsPreviousWorker"]'
      );
      if (radios.length >= 2) {
        console.log('[simpleApply:workday] -> previousWorker: No (fallback)');
        radios[1].click();
      }
    }
  });

  /* Name */
  await withOpt<HTMLInputElement>(
    [
      'input[data-automation-id="legalNameSection_firstName"]',
      'input[id="name--legalName--firstName"]',
      'input[name="legalName--firstName"]',
    ],
    (el) => { console.log('[simpleApply:workday] -> firstName'); fill(el, firstName); }
  );

  await withOpt<HTMLInputElement>(
    [
      'input[data-automation-id="legalNameSection_lastName"]',
      'input[id="name--legalName--lastName"]',
      'input[name="legalName--lastName"]',
    ],
    (el) => { console.log('[simpleApply:workday] -> lastName'); fill(el, lastName); }
  );

  /* Address */
  if (profile.address) {
    await withOpt<HTMLInputElement>(
      [
        'input[data-automation-id="addressSection_addressLine1"]',
        'input[id="address--addressLine1"]',
        'input[name="addressLine1"]',
      ],
      (el) => { console.log('[simpleApply:workday] -> address'); fill(el, profile.address!); }
    );
  }

  if (profile.city) {
    await withOpt<HTMLInputElement>(
      [
        'input[data-automation-id="addressSection_city"]',
        'input[id="address--city"]',
        'input[name="city"]',
      ],
      (el) => { console.log('[simpleApply:workday] -> city'); fill(el, profile.city!); }
    );
  }

  /* State/Region dropdown */
  if (profile.state) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="addressSection_countryRegion"]',
      async (el) => {
        console.log('[simpleApply:workday] -> state');
        await typeIntoDropdown(el, profile.state!);
      }
    );
  }

  if (profile.postalCode) {
    await withOpt<HTMLInputElement>(
      [
        'input[data-automation-id="addressSection_postalCode"]',
        'input[id="address--postalCode"]',
        'input[name="postalCode"]',
      ],
      (el) => { console.log('[simpleApply:workday] -> postalCode'); fill(el, profile.postalCode!); }
    );
  }

  /* Phone */
  if (profile.phoneType) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="phone-device-type"]',
      async (el) => {
        console.log('[simpleApply:workday] -> phoneType');
        await typeIntoDropdown(el, profile.phoneType!);
      }
    );
  }

  if (profile.phone) {
    await withOpt<HTMLInputElement>(
      [
        'input[data-automation-id="phone-number"]',
        'input[id="phoneNumber--phoneNumber"]',
        'input[name="phoneNumber"]',
      ],
      (el) => { console.log('[simpleApply:workday] -> phone'); fill(el, profile.phone!); }
    );
  }

  /* Click Next */
  await clickNext();
}

// ---------------------------------------------------------------------------
// fillExperience — mirrors reference repo apply.js fillExperience()
// ---------------------------------------------------------------------------

async function fillExperience(profile: ProfileData): Promise<void> {
  console.log('[simpleApply:workday] Filling experience');

  /* Work Experiences — index-based targeting to prevent overwrite */
  let addedWorks = 0;
  let weClicksTotal = 0;  // Track total Add clicks for work experience
  const WE_ANCHOR = 'input[name="jobTitle"]';  // one per form

  for (const work of profile.experiences ?? []) {
    addedWorks++;
    console.log(`[simpleApply:workday] Work experience #${addedWorks}: ${work.role} @ ${work.company} (${work.location})`);

    // Ensure the form for this index exists in DOM before trying to fill
    const currentCount = document.querySelectorAll(WE_ANCHOR).length;
    console.log(`[simpleApply:workday] [WE#${addedWorks}] Current jobTitle count: ${currentCount}, need: ${addedWorks}`);

    if (currentCount < addedWorks) {
      console.log(`[simpleApply:workday] [WE#${addedWorks}] Count insufficient, clicking Add button (click #${weClicksTotal + 1})...`);
      const ok = await clickAddInSection('div[data-automation-id="workExperienceSection"]', 'Add Work Experience');
      weClicksTotal++;
      if (!ok) {
        console.warn(`[simpleApply:workday] [WE#${addedWorks}] Could not add work experience, skipping remaining`);
        break;
      }
      console.log(`[simpleApply:workday] [WE#${addedWorks}] Waiting for jobTitle count to reach ${addedWorks}...`);
      await waitForFormCount(WE_ANCHOR, addedWorks, 5000);
      const afterCount = document.querySelectorAll(WE_ANCHOR).length;
      console.log(`[simpleApply:workday] [WE#${addedWorks}] After wait: jobTitle count = ${afterCount} (expected ${addedWorks})`);
    }

    const idx = addedWorks - 1;  // 0-based index for this specific form
    console.log(`[simpleApply:workday] [WE#${addedWorks}] Starting fill with index=${idx}`);

    // Job Title
    if (work.role) {
      const jobTitleEls = document.querySelectorAll<HTMLInputElement>('input[name="jobTitle"]');
      console.log(`[simpleApply:workday] [WE#${addedWorks}] jobTitle query returned ${jobTitleEls.length} elements, looking for index ${idx}`);
      if (jobTitleEls[idx]) {
        console.log(`[simpleApply:workday] [WE#${addedWorks}] -> jobTitle[${idx}]: "${work.role}"`);
        fill(jobTitleEls[idx], work.role);
      } else {
        console.warn(`[simpleApply:workday] [WE#${addedWorks}] No jobTitle element at index ${idx} (only ${jobTitleEls.length} exist)`);
      }
    }

    // Company
    if (work.company) {
      const companyEls = document.querySelectorAll<HTMLInputElement>('input[name="companyName"]');
      if (companyEls[idx]) {
        console.log(`[simpleApply:workday] -> company[${idx}]: "${work.company}"`);
        fill(companyEls[idx], work.company);
      }
    }

    // Location
    if (work.location) {
      const locationEls = document.querySelectorAll<HTMLInputElement>('input[name="location"]');
      if (locationEls[idx]) {
        console.log(`[simpleApply:workday] -> location[${idx}]: "${work.location}"`);
        fill(locationEls[idx], work.location);
      }
    }

    // Dates — parse "YYYY-MM" format, type char-by-char for React date inputs
    const [startYear, startMonth] = (work.start ?? '').split('-');
    const [endYear, endMonth] = (work.end ?? '').split('-');

    // Workday month fields normalize to single digit (e.g. "1" not "01")
    const startMonthNorm = startMonth ? String(parseInt(startMonth, 10)) : '';
    const endMonthNorm   = endMonth   ? String(parseInt(endMonth,   10)) : '';

    if (startMonthNorm) {
      const startMonthEls = document.querySelectorAll<HTMLInputElement>(
        'input[data-automation-id="dateSectionMonth-input"][id*="startDate"]'
      );
      console.log(`[simpleApply:workday] [date] startMonth els found: ${startMonthEls.length}, need idx=${idx}, value="${startMonthNorm}"`);
      if (startMonthEls[idx]) {
        console.log(`[simpleApply:workday] -> startMonth[${idx}]: "${startMonthNorm}" (before: "${startMonthEls[idx].value}")`);
        await typeChars(startMonthEls[idx], startMonthNorm);
        console.log(`[simpleApply:workday] [date] startMonth[${idx}] after fill: "${startMonthEls[idx].value}"`);
      } else {
        console.warn(`[simpleApply:workday] [date] startMonth[${idx}] NOT FOUND — ${startMonthEls.length} el(s) available`);
      }
    }

    if (startYear) {
      const startYearEls = document.querySelectorAll<HTMLInputElement>(
        'input[data-automation-id="dateSectionYear-input"][id*="startDate"]'
      );
      console.log(`[simpleApply:workday] [date] startYear els found: ${startYearEls.length}, need idx=${idx}, value="${startYear}"`);
      if (startYearEls[idx]) {
        console.log(`[simpleApply:workday] -> startYear[${idx}]: "${startYear}" (before: "${startYearEls[idx].value}")`);
        await typeChars(startYearEls[idx], startYear);
        console.log(`[simpleApply:workday] [date] startYear[${idx}] after fill: "${startYearEls[idx].value}"`);
      } else {
        console.warn(`[simpleApply:workday] [date] startYear[${idx}] NOT FOUND — ${startYearEls.length} el(s) available`);
      }
    }

    if (endMonthNorm) {
      const endMonthEls = document.querySelectorAll<HTMLInputElement>(
        'input[data-automation-id="dateSectionMonth-input"][id*="endDate"]'
      );
      console.log(`[simpleApply:workday] [date] endMonth els found: ${endMonthEls.length}, need idx=${idx}, value="${endMonthNorm}"`);
      if (endMonthEls[idx]) {
        console.log(`[simpleApply:workday] -> endMonth[${idx}]: "${endMonthNorm}" (before: "${endMonthEls[idx].value}")`);
        await typeChars(endMonthEls[idx], endMonthNorm);
        console.log(`[simpleApply:workday] [date] endMonth[${idx}] after fill: "${endMonthEls[idx].value}"`);
      } else {
        console.warn(`[simpleApply:workday] [date] endMonth[${idx}] NOT FOUND — ${endMonthEls.length} el(s) available`);
      }
    }

    if (endYear) {
      const endYearEls = document.querySelectorAll<HTMLInputElement>(
        'input[data-automation-id="dateSectionYear-input"][id*="endDate"]'
      );
      console.log(`[simpleApply:workday] [date] endYear els found: ${endYearEls.length}, need idx=${idx}, value="${endYear}"`);
      if (endYearEls[idx]) {
        console.log(`[simpleApply:workday] -> endYear[${idx}]: "${endYear}" (before: "${endYearEls[idx].value}")`);
        await typeChars(endYearEls[idx], endYear);
        console.log(`[simpleApply:workday] [date] endYear[${idx}] after fill: "${endYearEls[idx].value}"`);
      } else {
        console.warn(`[simpleApply:workday] [date] endYear[${idx}] NOT FOUND — ${endYearEls.length} el(s) available`);
      }
    }

    // Description
    if (work.description) {
      const descEls = document.querySelectorAll<HTMLTextAreaElement>('textarea[id*="roleDescription"]');
      if (descEls[idx]) {
        console.log(`[simpleApply:workday] -> description[${idx}]`);
        fill(descEls[idx], work.description);
      }
    }
  }

  /* Education — index-based targeting to prevent overwrite */
  const eduCount = profile.education?.length ?? 0;
  console.log(`[simpleApply:workday] Filling education (${eduCount} entries)`);

  let addedEdus = 0;
  let eduClicksTotal = 0;  // Track total Add clicks for education
  const EDU_ANCHOR = 'input[name="schoolName"]';

  for (const edu of profile.education ?? []) {
    addedEdus++;
    console.log(`[simpleApply:workday] [EDU#${addedEdus}] Processing: ${edu.school}`);

    // Ensure the form for this index exists in DOM before trying to fill
    const currentEduCount = document.querySelectorAll(EDU_ANCHOR).length;
    console.log(`[simpleApply:workday] [EDU#${addedEdus}] Current school input count: ${currentEduCount}, need: ${addedEdus}`);

    if (currentEduCount < addedEdus) {
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] Count insufficient, clicking Add button (click #${eduClicksTotal + 1})...`);
      const ok = await clickAddInSection('div[data-automation-id="educationSection"]', 'Add Education');
      eduClicksTotal++;
      if (!ok) {
        console.warn(`[simpleApply:workday] [EDU#${addedEdus}] Could not add education, skipping remaining`);
        break;
      }
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] Waiting for school input count to reach ${addedEdus}...`);
      await waitForFormCount(EDU_ANCHOR, addedEdus, 5000);
      const afterEduCount = document.querySelectorAll(EDU_ANCHOR).length;
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] After wait: school input count = ${afterEduCount} (expected ${addedEdus})`);

    }

    const idx = addedEdus - 1;  // 0-based index for this specific form
    console.log(`[simpleApply:workday] [EDU#${addedEdus}] Starting fill with index=${idx}`);

    // School input — type and Enter to select from search results
    if (edu.school) {
      const schoolEls = document.querySelectorAll<HTMLInputElement>('input[name="schoolName"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] school query returned ${schoolEls.length} elements, looking for index ${idx}`);
      if (schoolEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> school[${idx}]: "${edu.school}"`);
        fill(schoolEls[idx], edu.school);
        await delay(500);
        schoolEls[idx].dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
        await delay(1000);
        schoolEls[idx].dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
      } else {
        console.warn(`[simpleApply:workday] [EDU#${addedEdus}] No school input element at index ${idx}`);
      }
    }

    // Degree dropdown — button[name="degree"] confirmed by DOM inspection
    if (edu.degree) {
      const mappedDegree = mapDegreeToWorkday(edu.degree);
      const degreeEls = document.querySelectorAll<HTMLButtonElement>('button[name="degree"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] degree query returned ${degreeEls.length} elements`);
      if (degreeEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> degree[${idx}]: "${edu.degree}" → "${mappedDegree}"`);
        await typeIntoDropdown(degreeEls[idx], mappedDegree);
      } else {
        console.warn(`[simpleApply:workday] [EDU#${addedEdus}] No degree element at index ${idx}`);
      }
    }

    // Field of Study / Major
    if (edu.fieldOfStudy) {
      const fieldEls = document.querySelectorAll<HTMLInputElement>('input[id*="--fieldOfStudy"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] fieldOfStudy query returned ${fieldEls.length} elements`);
      if (fieldEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> fieldOfStudy[${idx}]: "${edu.fieldOfStudy}"`);
        fill(fieldEls[idx], edu.fieldOfStudy);
      }
    }

    // GPA
    if (edu.gpa) {
      const gpaEls = document.querySelectorAll<HTMLInputElement>('input[id*="--gradeAverage"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] gpa query returned ${gpaEls.length} elements`);
      if (gpaEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> gpa[${idx}]: "${edu.gpa}"`);
        fill(gpaEls[idx], edu.gpa);
      }
    }

    // Start / End years
    if (edu.startYear) {
      const startYearEls = document.querySelectorAll<HTMLInputElement>('input[id*="--firstYearAttended"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] startYear query returned ${startYearEls.length} elements`);
      if (startYearEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> startYear[${idx}]: "${edu.startYear}"`);
        fill(startYearEls[idx], edu.startYear);
      }
    }

    if (edu.endYear) {
      const endYearEls = document.querySelectorAll<HTMLInputElement>('input[id*="--lastYearAttended"]');
      console.log(`[simpleApply:workday] [EDU#${addedEdus}] endYear query returned ${endYearEls.length} elements`);
      if (endYearEls[idx]) {
        console.log(`[simpleApply:workday] [EDU#${addedEdus}] -> endYear[${idx}]: "${edu.endYear}"`);
        fill(endYearEls[idx], edu.endYear);
      }
    }
  }

  /* Skills — limited to MAX_SKILLS to avoid very long fills */
  if (profile.skills?.length) {
    const skillsToFill = profile.skills.slice(0, MAX_SKILLS);
    console.log(`[simpleApply:workday] Skills: filling ${skillsToFill.length} of ${profile.skills!.length}`);

    const skillInputSelectors = 'input[id="skills--skills"]';
    const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;

    // Confirm the input exists before looping
    const firstEl = await waitForSelector<HTMLInputElement>(skillInputSelectors, 3000);
    if (!firstEl) {
      console.warn('[simpleApply:workday] Skills input NOT found — skipping');
    } else {
      console.log(`[simpleApply:workday] Skills input confirmed: id="${firstEl.id}"`);

      for (let i = 0; i < skillsToFill.length; i++) {
        const skill = skillsToFill[i];

        // Re-query EVERY iteration — React remounts the input after each selection
        const el = document.querySelector<HTMLInputElement>(skillInputSelectors);
        console.log(`[simpleApply:workday] -> skill #${i + 1}/${skillsToFill.length}: "${skill}" — el.isConnected=${el?.isConnected}`);
        if (!el) { console.warn(`[simpleApply:workday] -> skill #${i + 1}: input gone, stopping`); break; }

        el.scrollIntoView({ block: 'center' });
        el.focus();
        await delay(200);

        // Set value via native setter
        if (nativeSetter) nativeSetter.call(el, skill); else el.value = skill;
        el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
        console.log(`[simpleApply:workday] -> skill #${i + 1}: typed "${el.value}"`);

        // Press Enter to open dropdown (Workday shows matching options on Enter)
        el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
        el.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', bubbles: true }));
        console.log(`[simpleApply:workday] -> skill #${i + 1}: Enter key pressed, waiting for dropdown...`);

        // Wait for dropdown to appear
        await delay(800);

        // Find available options: all promptOption elements NOT in selectedItemList
        const allPromptOptions = document.querySelectorAll('[data-automation-id="promptOption"]');
        const selectedItemsLists = document.querySelectorAll('[data-automation-id="selectedItemList"]');

        const availableOptions = Array.from(allPromptOptions).filter(option => {
          // Skip if this option is in a selected items list (already selected)
          for (const selectedList of selectedItemsLists) {
            if (selectedList.contains(option)) return false;
          }
          const text = option.textContent?.trim() || '';
          // Skip empty or "No Items" results
          return text !== '' && text !== 'No Items.';
        });

        console.log(`[simpleApply:workday] -> skill #${i + 1}: found ${availableOptions.length} dropdown options`);

        // Find best match: exact match or first result
        const skillLower = skill.toLowerCase();
        const bestMatch = availableOptions.find(
          option => (option.textContent?.trim().toLowerCase() || '') === skillLower
        ) || availableOptions[0];

        if (bestMatch) {
          const selectedText = bestMatch.textContent?.trim();
          console.log(`[simpleApply:workday] -> skill #${i + 1}: ✓ selecting "${selectedText}"`);
          (bestMatch as HTMLElement).click();
          await delay(500);
        } else {
          console.warn(`[simpleApply:workday] -> skill #${i + 1}: "${skill}" — no dropdown options found, skipping`);
          // Clear input for next skill
          if (nativeSetter) nativeSetter.call(el, ''); else el.value = '';
          el.dispatchEvent(new Event('input', { bubbles: true }));
          await delay(150);
        }
      }
    }
  }

  /* Resume Upload — inject from chrome.storage via DataTransfer */
  if (!resumeAlreadyUploaded()) {
    const uploadEl = document.querySelector<HTMLInputElement>(
      'input[data-automation-id="file-upload-input-ref"]'
    ) ?? document.querySelector<HTMLInputElement>('input[type="file"]');

    if (uploadEl) {
      console.log('[simpleApply:workday] -> resume: uploading from storage');
      const injected = await injectResume(uploadEl);
      if (injected) {
        const confirmed = await waitForUploadConfirmation();
        console.log(`[simpleApply:workday] -> resume: ${confirmed ? 'upload confirmed' : 'upload processing'}`);
      }
    } else {
      console.log('[simpleApply:workday] -> resume: no upload input found (skipping)');
    }
  } else {
    console.log('[simpleApply:workday] -> resume: already uploaded (skipping)');
  }

  /* Website Links */
  // Selector for all URL inputs inside the Websites group
  const websiteGroupInputSel = '[role="group"][aria-labelledby="Websites-section"] input, [aria-labelledby="Websites-section"] input';
  const websiteAddBtnSels = [
    '[role="group"][aria-labelledby="Websites-section"] button[data-automation-id="add-button"]',
    '[aria-labelledby="Websites-section"] button[data-automation-id="add-button"]',
  ];

  // Check if there is a dedicated LinkedIn input (some Workday forms have it)
  const dedicatedLinkedIn = document.querySelector<HTMLInputElement>(
    'input[name="linkedInAccount"], input[id*="linkedInAccount"], input[data-automation-id="linkedinQuestion"]'
  );
  if (dedicatedLinkedIn && profile.linkedin) {
    console.log(`[simpleApply:workday] -> linkedin: "${profile.linkedin}" (dedicated input)`);
    fill(dedicatedLinkedIn, profile.linkedin);

    // Clear any website panel that duplicates the LinkedIn URL (leftover from previous application)
    const linkedinNorm = profile.linkedin.toLowerCase().replace(/\/+$/, '');
    document.querySelectorAll<HTMLInputElement>(websiteGroupInputSel).forEach(inp => {
      if (inp.value.trim().toLowerCase().replace(/\/+$/, '') === linkedinNorm) {
        console.log(`[simpleApply:workday] [website] clearing duplicate LinkedIn from website panel`);
        fill(inp, '');
      }
    });
  }

  // Read existing website panel values — Workday persists them from previous applications
  const existingWebInputs = Array.from(document.querySelectorAll<HTMLInputElement>(websiteGroupInputSel));
  const existingValues = existingWebInputs.map(inp => inp.value.trim().toLowerCase()).filter(v => v !== '');
  console.log(`[simpleApply:workday] [website] existing values: [${existingValues.join(' | ')}]`);

  // Build the list of URLs that need a website panel entry (skip already-filled ones)
  const allWebsiteUrls: Array<{ name: string; url: string }> = [];
  if (!dedicatedLinkedIn && profile.linkedin) allWebsiteUrls.push({ name: 'linkedin',  url: profile.linkedin });
  if (profile.portfolio)                       allWebsiteUrls.push({ name: 'portfolio', url: profile.portfolio });
  if (profile.github)                          allWebsiteUrls.push({ name: 'github',    url: profile.github });

  const websiteUrls = allWebsiteUrls.filter(entry => {
    const normalised = entry.url.toLowerCase().replace(/\/+$/, '');
    const alreadyFilled = existingValues.some(v => v.replace(/\/+$/, '') === normalised);
    if (alreadyFilled) console.log(`[simpleApply:workday] [website] ${entry.name}: already filled — skipping`);
    return !alreadyFilled;
  });

  for (const entry of websiteUrls) {
    const prevCount = document.querySelectorAll(websiteGroupInputSel).length;
    console.log(`[simpleApply:workday] [website] ${entry.name}: current input count=${prevCount}`);

    // Click Add only if there is no pre-existing panel for this slot
    const clicked = await withOpt<HTMLButtonElement>(
      websiteAddBtnSels,
      async (el) => {
        const rect = el.getBoundingClientRect();
        console.warn(`[simpleApply:workday] [website] ⚠️ Clicking Add for ${entry.name}: text="${el.textContent?.trim()}" Y=${Math.round(rect.top)}`);
        el.click();
      }
    );

    if (!clicked) {
      console.warn(`[simpleApply:workday] [website] Add button NOT found for ${entry.name} — skipping`);
      continue;
    }

    // Wait (with MutationObserver) until a new input appears in the group
    await waitForFormCount(websiteGroupInputSel, prevCount + 1, 5000);

    const groupInputs = document.querySelectorAll<HTMLInputElement>(websiteGroupInputSel);
    console.log(`[simpleApply:workday] [website] After Add for ${entry.name}: ${groupInputs.length} input(s) in group`);
    groupInputs.forEach((inp, i) =>
      console.log(`[simpleApply:workday] [website]   group input[${i}]: name="${inp.name}" automation-id="${inp.getAttribute('data-automation-id')}"`)
    );

    // The newly added input is at index prevCount
    const newInput = groupInputs[prevCount] ?? null;
    if (newInput) {
      console.log(`[simpleApply:workday] -> ${entry.name}: "${entry.url}"`);
      fill(newInput, entry.url);
    } else {
      console.warn(`[simpleApply:workday] [website] ${entry.name} input NOT found after Add click (got ${groupInputs.length} inputs)`);
    }
  }

  // Summary of Add button clicks
  const totalClicks = weClicksTotal + eduClicksTotal;
  console.log(`[simpleApply:workday] === Experience filling complete: ${weClicksTotal} WE clicks + ${eduClicksTotal} EDU clicks = ${totalClicks} total ===`);

  /* Click Next */
  await clickNext();
}

// ---------------------------------------------------------------------------
// fillVoluntaryDisclosures — mirrors reference repo fillVoluntaryDisclosures()
// ---------------------------------------------------------------------------

async function fillVoluntaryDisclosures(profile: ProfileData): Promise<void> {
  const vd = profile.voluntaryDisclosures;
  if (!vd) { await clickNext(); return; }
  console.log('[simpleApply:workday] Filling voluntary disclosures');

  /* Gender */
  if (vd.gender) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="gender"]',
      async (el) => { await typeIntoDropdown(el, vd.gender!); }
    );
    await delay(200);
  }

  /* Hispanic or Latino */
  if (vd.hispanicOrLatino) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="hispanicOrLatino"]',
      async (el) => { await typeIntoDropdown(el, vd.hispanicOrLatino!); }
    );
  }

  /* Ethnicity */
  if (vd.ethnicity) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="ethnicityDropdown"]',
      async (el) => { await typeIntoDropdown(el, vd.ethnicity!); }
    );
    await delay(200);
  }

  /* Veteran Status */
  if (vd.veteranStatus) {
    await withOpt<HTMLButtonElement>(
      'button[data-automation-id="veteranStatus"]',
      async (el) => { await typeIntoDropdown(el, vd.veteranStatus!); }
    );
  }

  /* Agreement Checkbox */
  await withOpt<HTMLInputElement>(
    'input[data-automation-id="agreementCheckbox"]',
    (el) => { if (!el.checked) el.click(); }
  );

  /* Click Next */
  await clickNext();
}

// ---------------------------------------------------------------------------
// fillSelfIdentify — mirrors reference repo fillSelfIdentify()
// ---------------------------------------------------------------------------

async function fillSelfIdentify(profile: ProfileData): Promise<void> {
  const vd = profile.voluntaryDisclosures;
  console.log('[simpleApply:workday] Filling self-identification');

  /* Full Name */
  await withOpt<HTMLInputElement>(
    'input[data-automation-id="name"]',
    (el) => { if (profile.name) fill(el, profile.name); }
  );

  /* Today's Date — click date icon, then Today button */
  await withOpt<HTMLElement>(
    'div[data-automation-id="dateIcon"]',
    async (el) => {
      el.click();
      await delay(300);
      await withOpt<HTMLButtonElement>(
        'button[data-automation-id="datePickerSelectedToday"]',
        (btn) => btn.click()
      );
    }
  );

  /* Disability Status */
  if (vd?.disability) {
    // Reference repo uses hardcoded IDs — common across many Workday portals
    const idMap: Record<string, string> = {
      'yes': '64cbff5f364f10000ae7a421cf210000',
      'no': '64cbff5f364f10000aeec521b4ec0000',
      'abstain': '64cbff5f364f10000af3af293a050000',
    };
    const targetId = idMap[vd.disability];
    if (targetId) {
      const radio = document.querySelector<HTMLInputElement>(`input[id="${targetId}"]`);
      if (radio) {
        radio.click();
      } else {
        // Fallback: match by label text
        const labelMatch: Record<string, RegExp> = {
          'yes': /i have a disability/i,
          'no': /i do not have a disability/i,
          'abstain': /i don.t wish to answer|prefer not/i,
        };
        const regex = labelMatch[vd.disability];
        if (regex) {
          for (const label of document.querySelectorAll('label')) {
            if (regex.test(label.textContent ?? '')) {
              const forId = label.getAttribute('for');
              if (forId) {
                document.querySelector<HTMLInputElement>(`#${CSS.escape(forId)}`)?.click();
              } else {
                label.click();
              }
              break;
            }
          }
        }
      }
    }
  }

  /* Click Next */
  await clickNext();
}

// ---------------------------------------------------------------------------
// Main entry — mirrors reference repo apply() function flow
// ---------------------------------------------------------------------------

let _fillWorkdayRunning = false;

export async function fillWorkday(profile: ProfileData): Promise<void> {
  if (_fillWorkdayRunning) {
    console.warn('[simpleApply:workday] ⚠️ CONCURRENT CALL BLOCKED — fillWorkday already running. Ignoring this call.');
    console.warn('[simpleApply:workday]   Triggered by page:', document.querySelector('[data-automation-id]')?.getAttribute('data-automation-id') ?? '(unknown)');
    return;
  }
  _fillWorkdayRunning = true;
  console.log('[simpleApply:workday] Starting fillWorkday — profile:', {
    name: profile.name,
    email: profile.email,
    phone: profile.phone,
    address: profile.address,
    city: profile.city,
    postalCode: profile.postalCode,
    state: profile.state,
    experiences: profile.experiences?.length ?? 0,
    education: profile.education?.length ?? 0,
    skills: profile.skills?.length ?? 0,
    hasVoluntary: !!profile.voluntaryDisclosures,
  });

  // Detect which page we're on and fill from there.
  // Reference repo navigates: contact → experience → voluntary → selfIdentify
  // We start wherever the user currently is.

  const pageOrder: Array<{
    detect: () => boolean;
    fill: () => Promise<void>;
    name: string;
  }> = [
    {
      name: 'contactInformation',
      detect: () => {
        // Bail early if Page 2 section containers are visible — avoids false positive
        // from lingering Page 1 inputs in Workday's SPA DOM
        if (
          document.querySelector('div[data-automation-id="workExperienceSection"]') ||
          document.querySelector('div[data-automation-id="educationSection"]')
        ) return false;
        return (
          !!document.querySelector('div[data-automation-id="contactInformationPage"]') ||
          !!document.querySelector('input[name="legalName--firstName"]') ||
          !!document.querySelector('input[id="name--legalName--firstName"]')
        );
      },
      fill: () => fillBasicInfo(profile),
    },
    {
      name: 'myExperience',
      detect: () =>
        !!document.querySelector('div[data-automation-id="workExperienceSection"]') ||
        !!document.querySelector('div[data-automation-id="educationSection"]') ||
        !!document.querySelector('div[data-automation-id="myExperiencePage"]') ||
        !!document.querySelector('input[data-automation-id="jobTitle"]') ||
        !!document.querySelector('input[data-automation-id="file-upload-input-ref"]') ||
        !!document.querySelector('input[type="file"]'),
      fill: () => fillExperience(profile),
    },
    {
      name: 'voluntaryDisclosures',
      detect: () =>
        !!document.querySelector('div[data-automation-id="voluntaryDisclosuresPage"]') ||
        !!document.querySelector('button[data-automation-id="gender"]') ||
        !!document.querySelector('button[data-automation-id="ethnicityDropdown"]'),
      fill: () => fillVoluntaryDisclosures(profile),
    },
    {
      name: 'selfIdentification',
      detect: () =>
        !!document.querySelector('div[data-automation-id="selfIdentificationPage"]') ||
        !!document.querySelector('input[data-automation-id="name"]') ||
        !!document.querySelector('div[data-automation-id="dateIcon"]'),
      fill: () => fillSelfIdentify(profile),
    },
  ];

  // Find which page we're starting on
  let startIdx = pageOrder.findIndex((p) => p.detect());
  if (startIdx === -1) {
    // Unknown page — try filling basic info as fallback
    console.log('[simpleApply:workday] Unknown page, attempting fillBasicInfo');
    await fillBasicInfo(profile);
    startIdx = 1; // continue from experience
  }

  // Fill from current page forward
  for (let i = startIdx; i < pageOrder.length; i++) {
    const page = pageOrder[i];
    console.log(`[simpleApply:workday] === ${page.name} ===`);

    if (i > startIdx) {
      // Wait for Workday React page transition — poll for up to 8 seconds
      let detected = false;
      for (let attempt = 0; attempt < 16; attempt++) {
        await delay(500);
        if (page.detect()) {
          detected = true;
          break;
        }
      }
      if (!detected) {
        console.log(`[simpleApply:workday] ${page.name} not detected after 8s, stopping`);
        break;
      }
    }

    await page.fill();
    await delay(300);
  }

  _fillWorkdayRunning = false;
  console.log('[simpleApply:workday] fillWorkday complete');
}
