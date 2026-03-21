import type { ProfileData } from './profile-client.js';
import type { DetectedField, FieldType } from './fieldDetector.js';

const PROFILE_FIELD_MAP: Partial<Record<FieldType, keyof ProfileData>> = {
  email: 'email',
  phone: 'phone',
  linkedinUrl: 'linkedin',
  githubUrl: 'github',
  portfolioUrl: 'portfolio',
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
  // Fill static fields
  for (const { element, fieldType } of detectedFields) {
    let value: string | undefined;

    if (fieldType === 'firstName' || fieldType === 'lastName' || fieldType === 'fullName') {
      value = getNamePart(profile, fieldType);
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

  // Handle dynamic multi-entry sections (experience, education)
  if (profile.experiences?.length) {
    await fillExperienceSection(root, profile);
  }
}
