import type { ProfileData } from '../profile-client.js';

const EASY_APPLY_SELECTORS = [
  '.jobs-easy-apply-modal',
  '[data-test-modal-id="easy-apply-modal"]',
  '.jobs-easy-apply-content',
];

export function isLinkedInEasyApply(): boolean {
  return EASY_APPLY_SELECTORS.some((sel) => !!document.querySelector(sel));
}

function getModal(): Element | null {
  for (const sel of EASY_APPLY_SELECTORS) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
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
}

function waitForMutation(container: Element, timeout = 5000): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error('LinkedIn step mutation timeout'));
    }, timeout);

    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      observer.disconnect();
      resolve();
    });

    observer.observe(container, { childList: true, subtree: true });
  });
}

async function clickNextAndWait(modal: Element): Promise<boolean> {
  const nextBtn = modal.querySelector<HTMLButtonElement>(
    'button[aria-label*="Continue to next step"], button[aria-label*="Submit"], button[data-easy-apply-next-button]'
  );
  if (!nextBtn) return false;

  const container = modal;
  const promise = waitForMutation(container, 5000).catch(() => {/* ignore timeout */});
  nextBtn.click();
  await promise;
  return true;
}

function fillCurrentStep(modal: Element, profile: ProfileData): void {
  // First name
  const firstNameInput = modal.querySelector<HTMLInputElement>(
    'input[id*="firstName"], input[name*="firstName"], input[autocomplete="given-name"]'
  );
  if (firstNameInput) {
    const parts = profile.name.split(' ');
    fillInput(firstNameInput, parts[0] ?? '');
  }

  // Last name
  const lastNameInput = modal.querySelector<HTMLInputElement>(
    'input[id*="lastName"], input[name*="lastName"], input[autocomplete="family-name"]'
  );
  if (lastNameInput) {
    const parts = profile.name.split(' ');
    fillInput(lastNameInput, parts.slice(1).join(' '));
  }

  // Email
  const emailInput = modal.querySelector<HTMLInputElement>(
    'input[type="email"], input[id*="email"], input[name*="email"]'
  );
  if (emailInput && profile.email) fillInput(emailInput, profile.email);

  // Phone
  const phoneInput = modal.querySelector<HTMLInputElement>(
    'input[type="tel"], input[id*="phone"], input[name*="phone"]'
  );
  if (phoneInput && profile.phone) fillInput(phoneInput, profile.phone);

  // LinkedIn URL (some forms ask for it)
  const linkedinInput = modal.querySelector<HTMLInputElement>(
    'input[id*="linkedin"], input[name*="linkedin"], input[placeholder*="linkedin" i]'
  );
  if (linkedinInput && profile.linkedin) fillInput(linkedinInput, profile.linkedin);
}

export async function fillLinkedIn(profile: ProfileData): Promise<void> {
  const modal = getModal();
  if (!modal) return;

  const MAX_STEPS = 10;
  for (let step = 0; step < MAX_STEPS; step++) {
    fillCurrentStep(modal, profile);

    const hasNext = await clickNextAndWait(modal);
    if (!hasNext) break;
  }
}
