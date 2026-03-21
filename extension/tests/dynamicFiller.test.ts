import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fillForm } from '../utils/dynamicFiller.js';
import { detectFields } from '../utils/fieldDetector.js';
import type { ProfileData } from '../utils/profile-client.js';

const PROFILE: ProfileData = {
  name: 'Alice Dupont',
  email: 'alice@example.com',
  phone: '+33 6 00 00 00 00',
  linkedin: 'https://linkedin.com/in/alice',
  github: 'https://github.com/alice',
  portfolio: 'https://alice.dev',
  experiences: [
    { company: 'Acme Corp', role: 'Engineer', start: '2020-01' },
  ],
};

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('fillForm', () => {
  it('fills a simple text input (firstName) from profile', async () => {
    document.body.innerHTML = '<form><input type="text" name="firstName" /></form>';
    const form = document.querySelector('form')!;
    const fields = detectFields(form);
    await fillForm(form, PROFILE, fields);
    const input = document.querySelector<HTMLInputElement>('input[name="firstName"]')!;
    expect(input.value).toBe('Alice');
  });

  it('fills email field from profile', async () => {
    document.body.innerHTML = '<form><input type="email" autocomplete="email" /></form>';
    const form = document.querySelector('form')!;
    const fields = detectFields(form);
    await fillForm(form, PROFILE, fields);
    const input = document.querySelector<HTMLInputElement>('input[type="email"]')!;
    expect(input.value).toBe('alice@example.com');
  });

  it('clicks Add-button and waits for MutationObserver before filling', async () => {
    document.body.innerHTML = `
      <form>
        <button aria-label="Add experience" type="button">Add experience</button>
      </form>
    `;
    const form = document.querySelector('form')!;
    const addBtn = document.querySelector<HTMLButtonElement>('button')!;

    // Simulate DOM mutation when button is clicked
    addBtn.addEventListener('click', () => {
      const companyInput = document.createElement('input');
      companyInput.name = 'company';
      companyInput.type = 'text';
      const roleInput = document.createElement('input');
      roleInput.name = 'title';
      roleInput.type = 'text';
      form.appendChild(companyInput);
      form.appendChild(roleInput);
    });

    const fields = detectFields(form);
    await fillForm(form, PROFILE, fields);

    const company = document.querySelector<HTMLInputElement>('input[name="company"]');
    const role = document.querySelector<HTMLInputElement>('input[name="title"]');
    expect(company?.value).toBe('Acme Corp');
    expect(role?.value).toBe('Engineer');
  });

  it('does not error when no Add-button exists', async () => {
    document.body.innerHTML = '<form><input type="email" autocomplete="email" /></form>';
    const form = document.querySelector('form')!;
    const fields = detectFields(form);
    await expect(fillForm(form, PROFILE, fields)).resolves.toBeUndefined();
  });

  it('fills lastName correctly by splitting full name', async () => {
    document.body.innerHTML = '<form><input type="text" name="lastName" /></form>';
    const form = document.querySelector('form')!;
    const fields = detectFields(form);
    await fillForm(form, PROFILE, fields);
    const input = document.querySelector<HTMLInputElement>('input[name="lastName"]')!;
    expect(input.value).toBe('Dupont');
  });
});
