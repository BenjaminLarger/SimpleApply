import { queryShadowAll } from '../shadowDom.js';
import type { ProfileData } from '../profile-client.js';

const WORKDAY_INDICATORS = [
  'wd-text-input',
  '[data-automation-id="legalNameSection"]',
  '[data-automation-id="email"]',
  '.WDAY-',
  'workday-web',
];

export function isWorkday(): boolean {
  // Check URL first — most reliable signal
  const urlMatch = /myworkdayjobs\.com|workday\.com/i.test(window.location.hostname);
  if (urlMatch) {
    console.log('[simpleApply:workday] isWorkday=true (URL match:', window.location.hostname, ')');
    return true;
  }
  const domMatch = WORKDAY_INDICATORS.some(
    (sel) => !!document.querySelector(sel) || !!document.querySelector(`[class*="wd-"]`)
  );
  console.log('[simpleApply:workday] isWorkday=', domMatch, '(DOM indicators)');
  return domMatch;
}

function fillInput(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const nativeSetter = Object.getOwnPropertyDescriptor(
    el instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype,
    'value'
  )?.set;
  if (nativeSetter) {
    nativeSetter.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
}

function waitForMutation(root: Element, timeout = 5000): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => { observer.disconnect(); resolve(); }, timeout);
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      observer.disconnect();
      resolve();
    });
    observer.observe(root, { childList: true, subtree: true });
  });
}

async function clickNextPage(timeout = 5000): Promise<boolean> {
  const nextBtn = document.querySelector<HTMLButtonElement>(
    '[data-automation-id="bottom-navigation-next-button"], button[aria-label*="Next"], button[title*="Next"]'
  );
  if (!nextBtn || nextBtn.disabled) return false;

  const promise = waitForMutation(document.body, timeout);
  nextBtn.click();
  await promise;
  return true;
}

function getInputSignature(input: HTMLInputElement): string {
  // Concatenate all identifying attributes into one string for matching
  return [
    input.getAttribute('name') ?? '',
    input.id ?? '',
    input.getAttribute('aria-label') ?? '',
    input.getAttribute('placeholder') ?? '',
    input.getAttribute('data-automation-id') ?? '',
  ].join(' ').toLowerCase();
}

function fillPage(profile: ProfileData): void {
  const root = document.documentElement;
  const nameParts = profile.name.split(' ');

  // Workday uses shadow DOM — pierce it with queryShadowAll
  const allInputs = queryShadowAll<HTMLInputElement>(root, 'input[type="text"], input[type="email"], input[type="tel"]');

  console.log(`[simpleApply:workday] fillPage: found ${allInputs.length} inputs, profile:`, {
    name: profile.name,
    email: profile.email,
    phone: profile.phone,
  });

  for (const input of allInputs) {
    const sig = getInputSignature(input);

    console.log(`[simpleApply:workday] Checking input: "${sig}"`);

    // Match by name/id patterns (Workday uses legalName--firstName, phoneNumber--phoneNumber, etc.)
    if (/firstname|first.?name|given.?name/i.test(sig) && !/middle/i.test(sig)) {
      console.log('[simpleApply:workday] → Filling firstName:', nameParts[0]);
      fillInput(input, nameParts[0] ?? '');
    } else if (/lastname|last.?name|family.?name|surname/i.test(sig) && !/secondary/i.test(sig)) {
      console.log('[simpleApply:workday] → Filling lastName:', nameParts.slice(1).join(' '));
      fillInput(input, nameParts.slice(1).join(' '));
    } else if (/email/i.test(sig)) {
      if (profile.email) {
        console.log('[simpleApply:workday] → Filling email:', profile.email);
        fillInput(input, profile.email);
      }
    } else if (/phonenumber--phonenumber|phone.?number$/i.test(sig) && !/country|extension|ext/i.test(sig)) {
      // Only fill the actual phone number field, not country code or extension
      if (profile.phone) {
        console.log('[simpleApply:workday] → Filling phone:', profile.phone);
        fillInput(input, profile.phone);
      }
    } else if (/addressline1|street.?address/i.test(sig)) {
      if (profile.address) {
        console.log('[simpleApply:workday] → Filling address:', profile.address);
        fillInput(input, profile.address);
      }
    } else if (/(?:^|\s|-)city|address--city/i.test(sig) && !/capacity/i.test(sig)) {
      if (profile.city) {
        console.log('[simpleApply:workday] → Filling city:', profile.city);
        fillInput(input, profile.city);
      }
    } else if (/postalcode|postal.?code|zip/i.test(sig)) {
      if (profile.postalCode) {
        console.log('[simpleApply:workday] → Filling postalCode:', profile.postalCode);
        fillInput(input, profile.postalCode);
      }
    } else if (/linkedin/i.test(sig)) {
      if (profile.linkedin) {
        console.log('[simpleApply:workday] → Filling linkedin:', profile.linkedin);
        fillInput(input, profile.linkedin);
      }
    } else {
      console.log('[simpleApply:workday] → No match for:', sig);
    }
  }
}

export async function fillWorkday(profile: ProfileData): Promise<void> {
  const MAX_PAGES = 8;

  for (let page = 0; page < MAX_PAGES; page++) {
    fillPage(profile);

    const hasNext = await clickNextPage(5000);
    if (!hasNext) break;

    // Brief pause for Workday's React state to settle
    await new Promise((r) => setTimeout(r, 300));
  }
}
