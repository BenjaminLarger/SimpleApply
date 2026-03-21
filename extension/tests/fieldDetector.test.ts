import { describe, it, expect, beforeEach } from 'vitest';
import { detectFields } from '../utils/fieldDetector.js';

function makeInput(attrs: Record<string, string>, tag: 'input' | 'textarea' = 'input'): HTMLElement {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v);
  }
  return el;
}

function wrapInForm(...elements: HTMLElement[]): HTMLFormElement {
  const form = document.createElement('form');
  for (const el of elements) form.appendChild(el);
  document.body.appendChild(form);
  return form;
}

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('detectFields', () => {
  it('detects email field by autocomplete attribute', () => {
    const input = makeInput({ type: 'email', autocomplete: 'email' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(1);
    expect(fields[0].fieldType).toBe('email');
    expect(fields[0].confidence).toBe(1.0);
  });

  it('detects firstName by name attribute', () => {
    const input = makeInput({ type: 'text', name: 'firstName' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(1);
    expect(fields[0].fieldType).toBe('firstName');
  });

  it('detects LinkedIn URL field by placeholder text', () => {
    const input = makeInput({ type: 'url', placeholder: 'Your LinkedIn profile URL' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(1);
    expect(fields[0].fieldType).toBe('linkedinUrl');
  });

  it('returns no result for unrecognised field', () => {
    const input = makeInput({ type: 'text', name: 'fooBarUnknownXyz123' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(0);
  });

  it('detects French label — prénom → firstName', () => {
    const label = document.createElement('label');
    label.setAttribute('for', 'fn');
    label.textContent = 'Prénom';
    const input = makeInput({ type: 'text', id: 'fn' });
    const form = wrapInForm(label, input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(1);
    expect(fields[0].fieldType).toBe('firstName');
  });

  it('detects Spanish label — apellido → lastName', () => {
    const label = document.createElement('label');
    label.setAttribute('for', 'ln');
    label.textContent = 'Apellido';
    const input = makeInput({ type: 'text', id: 'ln' });
    const form = wrapInForm(label, input);
    const fields = detectFields(form);
    expect(fields).toHaveLength(1);
    expect(fields[0].fieldType).toBe('lastName');
  });

  it('detects phone field by name attribute', () => {
    const input = makeInput({ type: 'tel', name: 'phone' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields[0].fieldType).toBe('phone');
  });

  it('detects GitHub URL field by id', () => {
    const input = makeInput({ type: 'url', id: 'githubUrl' });
    const form = wrapInForm(input);
    const fields = detectFields(form);
    expect(fields[0].fieldType).toBe('githubUrl');
  });

  it('skips hidden, submit, and button inputs', () => {
    const hidden = makeInput({ type: 'hidden', name: 'email' });
    const submit = makeInput({ type: 'submit', name: 'email' });
    const form = wrapInForm(hidden, submit);
    const fields = detectFields(form);
    expect(fields).toHaveLength(0);
  });
});
