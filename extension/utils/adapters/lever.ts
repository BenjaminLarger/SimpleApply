import type { ProfileData } from '../profile-client.js';

export function isLever(): boolean {
  return (
    !!document.querySelector('.lever-apply, [data-lever-application], .postings-page') ||
    /lever\.co/.test(window.location.hostname)
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
}

/**
 * Lever uses custom dropdown components triggered by click.
 * Find the trigger, click it, then select the matching option.
 */
async function fillCustomDropdown(
  container: Element,
  selector: string,
  value: string
): Promise<void> {
  const trigger = container.querySelector<HTMLElement>(selector);
  if (!trigger) return;

  trigger.click();

  // Wait for dropdown options to render
  await new Promise<void>((resolve) => {
    const observer = new MutationObserver(() => {
      observer.disconnect();
      resolve();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => { observer.disconnect(); resolve(); }, 500);
  });

  // Find and click matching option
  const options = Array.from(document.querySelectorAll<HTMLElement>(
    '[role="option"], .dropdown-option, .select-option, li.option'
  ));
  const match = options.find((opt) =>
    opt.textContent?.toLowerCase().includes(value.toLowerCase())
  );
  if (match) match.click();
}

export async function fillLever(profile: ProfileData): Promise<void> {
  const root = document.querySelector('.application-form, form[id*="application"]') ?? document.documentElement;
  const nameParts = profile.name.split(' ');

  // Standard text inputs
  const nameInput = root.querySelector<HTMLInputElement>(
    'input[name="name"], input[id*="name"]:not([id*="last"]):not([id*="company"])'
  );
  const emailInput = root.querySelector<HTMLInputElement>('input[type="email"], input[name="email"]');
  const phoneInput = root.querySelector<HTMLInputElement>('input[type="tel"], input[name="phone"]');
  const linkedinInput = root.querySelector<HTMLInputElement>(
    'input[name*="linkedin"], input[placeholder*="linkedin" i]'
  );
  const githubInput = root.querySelector<HTMLInputElement>(
    'input[name*="github"], input[placeholder*="github" i]'
  );

  if (nameInput) fillInput(nameInput, profile.name);
  if (emailInput && profile.email) fillInput(emailInput, profile.email);
  if (phoneInput && profile.phone) fillInput(phoneInput, profile.phone);
  if (linkedinInput && profile.linkedin) fillInput(linkedinInput, profile.linkedin);
  if (githubInput && profile.github) fillInput(githubInput, profile.github);

  // Lever custom dropdowns (e.g. location, source)
  const locationDropdown = root.querySelector<HTMLElement>('[data-field="location"] .trigger, .location-dropdown');
  if (locationDropdown) {
    const cityParts = nameParts; // placeholder — use profile city if available
    await fillCustomDropdown(root, '[data-field="location"] .trigger', cityParts[0] ?? '');
  }
}
