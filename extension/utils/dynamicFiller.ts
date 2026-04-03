import type { ProfileData } from './profile-client.js';
import type { DetectedField, FieldType } from './fieldDetector.js';

const PROFILE_FIELD_MAP: Partial<Record<FieldType, keyof ProfileData>> = {
  email: 'email',
  phone: 'phone',
  linkedinUrl: 'linkedin',
  githubUrl: 'github',
  portfolioUrl: 'portfolio',
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

  // Handle dynamic multi-entry sections (experience, education)
  if (profile.experiences?.length) {
    await fillExperienceSection(root, profile);
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
        console.log('[simpleApply:filler] Country select filled:', countryCode);
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
 * Find matching country option in select
 */
function findCountryOption(select: HTMLSelectElement, countryName: string): string | null {
  const countryMap: Record<string, string> = {
    'Canada': 'CA',
    'United States': 'US',
    'United Kingdom': 'GB',
    'Germany': 'DE',
    'France': 'FR',
    'Australia': 'AU',
    'India': 'IN',
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
