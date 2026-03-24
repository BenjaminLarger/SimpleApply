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

  /* Work Experiences */
  let addedWorks = 0;
  for (const work of profile.experiences ?? []) {
    addedWorks++;

    if (!(await selectorExists(`div[data-automation-id="workExperience-${addedWorks}"]`))) {
      if (addedWorks === 1) {
        // add first section (lowercase "add")
        await withOpt<HTMLButtonElement>(
          [
            'div[data-automation-id="workExperienceSection"] button[data-automation-id*="add"]',
            'button[aria-label*="Add Work Experience"]',
          ],
          async (el) => { el.click(); await delay(500); },
          5000
        );
      } else {
        // add additional sections (uppercase "Add")
        await withOpt<HTMLButtonElement>(
          [
            'div[data-automation-id="workExperienceSection"] button[data-automation-id*="Add"]',
            'button[aria-label*="Add Another"]',
          ],
          async (el) => { el.click(); await delay(500); },
          5000
        );
      }
    }

    const prefix = `div[data-automation-id="workExperience-${addedWorks}"]`;

    if (work.role) {
      await withOpt<HTMLInputElement>(
        [`${prefix} input[data-automation-id="jobTitle"]`],
        (el) => fill(el, work.role)
      );
    }
    await withOpt<HTMLInputElement>(
      [`${prefix} input[data-automation-id="company"]`],
      (el) => fill(el, work.company)
    );
    if (work.location) {
      await withOpt<HTMLInputElement>(
        [`${prefix} input[data-automation-id="location"]`],
        (el) => fill(el, work.location!)
      );
    }

    // Dates — parse "YYYY-MM" format
    const [startYear, startMonth] = (work.start ?? '').split('-');
    const [endYear, endMonth] = (work.end ?? '').split('-');

    if (startMonth) {
      await withOpt<HTMLInputElement>(
        [`${prefix} div[data-automation-id="formField-startDate"] input[data-automation-id="dateSectionMonth-input"]`],
        async (el) => { el.focus(); fill(el, startMonth); }
      );
    }
    if (startYear) {
      await withOpt<HTMLInputElement>(
        [`${prefix} div[data-automation-id="formField-startDate"] input[data-automation-id="dateSectionYear-input"]`],
        async (el) => { el.focus(); fill(el, startYear); }
      );
    }
    if (endMonth) {
      await withOpt<HTMLInputElement>(
        [`${prefix} div[data-automation-id="formField-endDate"] input[data-automation-id="dateSectionMonth-input"]`],
        async (el) => { el.focus(); fill(el, endMonth); }
      );
    }
    if (endYear) {
      await withOpt<HTMLInputElement>(
        [`${prefix} div[data-automation-id="formField-endDate"] input[data-automation-id="dateSectionYear-input"]`],
        async (el) => { el.focus(); fill(el, endYear); }
      );
    }

    if (work.description) {
      await withOpt<HTMLTextAreaElement>(
        [`${prefix} textarea[data-automation-id="description"]`],
        (el) => fill(el, work.description!)
      );
    }
  }

  /* Education — Add first education */
  const edu = profile.education?.[0];
  if (edu) {
    await withOpt<HTMLButtonElement>(
      [
        'div[data-automation-id="educationSection"] button[data-automation-id="Add"]',
        'div[data-automation-id="educationSection"] button[data-automation-id*="add"]',
      ],
      (el) => el.click()
    );
    await delay(500);

    // School input — type and Enter to select from search results
    if (edu.school) {
      await withOpt<HTMLInputElement>(
        'div[data-automation-id="formField-schoolItem"] input',
        async (el) => {
          console.log('[simpleApply:workday] -> school');
          fill(el, edu.school);
          await delay(500);
          el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
          await delay(1000);
          el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
        }
      );
    }

    // Degree dropdown
    if (edu.degree) {
      await withOpt<HTMLButtonElement>(
        'button[data-automation-id="degree"]',
        async (el) => {
          console.log('[simpleApply:workday] -> degree');
          await typeIntoDropdown(el, edu.degree);
        }
      );
    }

    // GPA
    if (edu.gpa) {
      await withOpt<HTMLInputElement>(
        'input[data-automation-id="gpa"]',
        (el) => { console.log('[simpleApply:workday] -> gpa'); fill(el, edu.gpa!); }
      );
    }

    // Start / End years
    if (edu.startYear) {
      await withOpt<HTMLInputElement>(
        'div[data-automation-id="formField-firstYearAttended"] input',
        (el) => fill(el, edu.startYear!)
      );
    }
    if (edu.endYear) {
      await withOpt<HTMLInputElement>(
        'div[data-automation-id="formField-lastYearAttended"] input',
        (el) => fill(el, edu.endYear!)
      );
    }
  }

  /* Skills */
  if (profile.skills?.length) {
    await withOpt<HTMLInputElement>(
      'div[data-automation-id="formField-skillsPrompt"] input',
      async (el) => {
        console.log('[simpleApply:workday] -> skills:', profile.skills!.length);
        for (const skill of profile.skills!) {
          fill(el, skill);
          await delay(300);
          el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
          await delay(5000);
          el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
        }
      }
    );
  }

  /* Resume Upload */
  if (await selectorExists('input[data-automation-id="file-upload-input-ref"]')) {
    console.log('[simpleApply:workday] Resume upload found — triggering file dialog');
    const uploadEl = document.querySelector<HTMLInputElement>('input[data-automation-id="file-upload-input-ref"]');
    if (uploadEl) uploadEl.click();
  }

  /* Website Links */
  let addedWebs = 0;
  if (profile.linkedin) {
    const linkedInInput = document.querySelector<HTMLInputElement>(
      'input[data-automation-id="linkedinQuestion"]'
    );
    if (linkedInInput) {
      console.log('[simpleApply:workday] -> linkedin (dedicated)');
      fill(linkedInInput, profile.linkedin);
    } else {
      // Must use a generic website box
      addedWebs++;
      if (!(await selectorExists(`div[data-automation-id="websitePanelSet-${addedWebs}"] input`))) {
        await withOpt<HTMLButtonElement>(
          'div[data-automation-id="websiteSection"] button[data-automation-id="Add"]',
          async (el) => { el.click(); await delay(300); }
        );
      }
      const webInput = document.querySelector<HTMLInputElement>(
        `div[data-automation-id="websitePanelSet-${addedWebs}"] input`
      );
      if (webInput) fill(webInput, profile.linkedin);
    }
  }

  if (profile.github) {
    addedWebs++;
    if (!(await selectorExists(`div[data-automation-id="websitePanelSet-${addedWebs}"] input`))) {
      await withOpt<HTMLButtonElement>(
        'div[data-automation-id="websiteSection"] button[data-automation-id="Add"]',
        async (el) => { el.click(); await delay(300); }
      );
    }
    const webInput = document.querySelector<HTMLInputElement>(
      `div[data-automation-id="websitePanelSet-${addedWebs}"] input`
    );
    if (webInput) fill(webInput, profile.github);
  }

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

export async function fillWorkday(profile: ProfileData): Promise<void> {
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
      detect: () =>
        !!document.querySelector('div[data-automation-id="contactInformationPage"]') ||
        !!document.querySelector('input[name="legalName--firstName"]') ||
        !!document.querySelector('input[id="name--legalName--firstName"]'),
      fill: () => fillBasicInfo(profile),
    },
    {
      name: 'myExperience',
      detect: () =>
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

  console.log('[simpleApply:workday] fillWorkday complete');
}
