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
  return WORKDAY_INDICATORS.some(
    (sel) => !!document.querySelector(sel) || !!document.querySelector(`[class*="wd-"]`)
  );
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

function fillPage(profile: ProfileData): void {
  const root = document.documentElement;
  const nameParts = profile.name.split(' ');

  // Workday uses shadow DOM — pierce it with queryShadowAll
  const allInputs = queryShadowAll<HTMLInputElement>(root, 'input[data-automation-id], input[type="text"], input[type="email"], input[type="tel"]');

  for (const input of allInputs) {
    const automationId = input.getAttribute('data-automation-id') ?? '';
    const label = (
      input.getAttribute('aria-label') ??
      input.getAttribute('placeholder') ??
      automationId
    ).toLowerCase();

    if (/first.?name|legal.?first/i.test(label) || automationId === 'firstName') {
      fillInput(input, nameParts[0] ?? '');
    } else if (/last.?name|legal.?last/i.test(label) || automationId === 'lastName') {
      fillInput(input, nameParts.slice(1).join(' '));
    } else if (/email/i.test(label) || automationId === 'email') {
      if (profile.email) fillInput(input, profile.email);
    } else if (/phone|mobile/i.test(label) || automationId === 'phone') {
      if (profile.phone) fillInput(input, profile.phone);
    } else if (/linkedin/i.test(label)) {
      if (profile.linkedin) fillInput(input, profile.linkedin);
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
