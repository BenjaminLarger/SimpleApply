import { describe, it, expect, beforeEach } from 'vitest';
import { queryShadowAll } from '../utils/shadowDom.js';

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('queryShadowAll', () => {
  it('finds elements in a flat DOM', () => {
    document.body.innerHTML = '<input type="text" /><input type="email" />';
    const results = queryShadowAll(document.body, 'input');
    expect(results).toHaveLength(2);
  });

  it('finds elements inside a single shadow root', () => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const shadow = host.attachShadow({ mode: 'open' });
    shadow.innerHTML = '<input type="text" />';

    const results = queryShadowAll<HTMLInputElement>(document.body, 'input');
    expect(results).toHaveLength(1);
    expect(results[0].type).toBe('text');
  });

  it('finds elements nested two shadow roots deep', () => {
    const host1 = document.createElement('div');
    document.body.appendChild(host1);
    const shadow1 = host1.attachShadow({ mode: 'open' });

    const host2 = document.createElement('div');
    shadow1.appendChild(host2);
    const shadow2 = host2.attachShadow({ mode: 'open' });
    shadow2.innerHTML = '<input type="email" />';

    const results = queryShadowAll<HTMLInputElement>(document.body, 'input');
    expect(results).toHaveLength(1);
    expect(results[0].type).toBe('email');
  });

  it('returns empty array when no matches', () => {
    document.body.innerHTML = '<div><span>hello</span></div>';
    const results = queryShadowAll(document.body, 'input');
    expect(results).toHaveLength(0);
  });

  it('finds elements both in flat DOM and shadow root', () => {
    document.body.innerHTML = '<input type="text" id="flat" />';
    const host = document.createElement('div');
    document.body.appendChild(host);
    const shadow = host.attachShadow({ mode: 'open' });
    shadow.innerHTML = '<input type="email" id="shadow" />';

    const results = queryShadowAll<HTMLInputElement>(document.body, 'input');
    expect(results).toHaveLength(2);
  });
});
