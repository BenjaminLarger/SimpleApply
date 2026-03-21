import type { ProfileData } from '../profile-client.js';

export function isGreenhouse(): boolean {
  return (
    !!document.querySelector('#greenhouse-app, .greenhouse-page, form[action*="greenhouse"]') ||
    /greenhouse\.io/.test(window.location.hostname)
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

export function fillGreenhouse(profile: ProfileData): void {
  const form = document.querySelector<HTMLFormElement>('#application_form, form.application');
  const root = form ?? document.documentElement;

  const nameParts = profile.name.split(' ');

  const firstName = root.querySelector<HTMLInputElement>('#first_name, input[name="job_application[first_name]"]');
  const lastName = root.querySelector<HTMLInputElement>('#last_name, input[name="job_application[last_name]"]');
  const email = root.querySelector<HTMLInputElement>('#email, input[name="job_application[email]"]');
  const phone = root.querySelector<HTMLInputElement>('#phone, input[name="job_application[phone]"]');
  const linkedin = root.querySelector<HTMLInputElement>(
    'input[id*="linkedin"], input[name*="linkedin"]'
  );
  const resumeUrl = root.querySelector<HTMLInputElement>(
    'input[id*="resume_url"], input[name*="resume_url"]'
  );

  if (firstName) fillInput(firstName, nameParts[0] ?? '');
  if (lastName) fillInput(lastName, nameParts.slice(1).join(' '));
  if (email && profile.email) fillInput(email, profile.email);
  if (phone && profile.phone) fillInput(phone, profile.phone);
  if (linkedin && profile.linkedin) fillInput(linkedin, profile.linkedin);
  if (resumeUrl && profile.portfolio) fillInput(resumeUrl, profile.portfolio);
}
