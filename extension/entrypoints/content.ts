import { defineContentScript } from 'wxt/sandbox';
import { detectFields } from '../utils/fieldDetector.js';
import { queryShadowAll } from '../utils/shadowDom.js';
import { fillForm } from '../utils/dynamicFiller.js';
import { getProfile } from '../utils/profile-client.js';
import { isWorkday, fillWorkday } from '../utils/adapters/workday.js';

const MIN_FIELDS = 3;
let bannerInjected = false;
let lastFieldCount = 0;

export default defineContentScript({
  matches: ['<all_urls>'],
  async main() {
    console.log('[simpleApply] Content script loaded on:', window.location.href);

    // Handle messages from popup
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
      console.log('[simpleApply] Received message:', message?.type);
      if (message?.type === 'GET_FIELD_COUNT') {
        // Detect on demand so the popup always gets fresh count
        const fields = detectFields(document.documentElement);
        const workday = isWorkday();
        const inputs = countInputs();
        const shadowInputs = queryShadowAll<HTMLInputElement>(document.documentElement, 'input').length;
        const count = workday ? Math.max(inputs, shadowInputs, fields.length) : fields.length;
        console.log('[simpleApply] GET_FIELD_COUNT →', {
          detectedFields: fields.length,
          standardInputs: inputs,
          shadowInputs,
          isWorkday: workday,
          reportedCount: count,
          fieldTypes: fields.map(f => `${f.fieldType}(${f.confidence})`),
        });
        sendResponse({ count });
      } else if (message?.type === 'MANUAL_FILL') {
        // Detect and fill on demand — don't rely on earlier detection
        manualFill();
      }
    });

    if (document.readyState === 'loading') {
      console.log('[simpleApply] Waiting for DOMContentLoaded...');
      document.addEventListener('DOMContentLoaded', () => tryDetect());
    } else {
      console.log('[simpleApply] DOM already ready, detecting now...');
      tryDetect();
    }

    // Watch for dynamically loaded fields (SPAs like Workday)
    let mutationCount = 0;
    const observer = new MutationObserver(debounce(() => {
      mutationCount++;
      console.log(`[simpleApply] MutationObserver fired (#${mutationCount}), re-detecting...`);
      tryDetect();
    }, 1500));
    observer.observe(document.body ?? document.documentElement, {
      childList: true,
      subtree: true,
    });

    // Stop observing after 60s to handle slow SPAs
    setTimeout(() => {
      observer.disconnect();
      console.log(`[simpleApply] MutationObserver disconnected after 60s (fired ${mutationCount} times)`);
    }, 60_000);
  },
});

function debounce(fn: () => void, ms: number): () => void {
  let timer: ReturnType<typeof setTimeout>;
  return () => {
    clearTimeout(timer);
    timer = setTimeout(fn, ms);
  };
}

function countInputs(): number {
  const count = document.querySelectorAll<HTMLInputElement>(
    'input[type="text"], input[type="email"], input[type="tel"], input[type="url"], textarea'
  ).length;
  return count;
}

function tryDetect(): void {
  if (bannerInjected) {
    console.log('[simpleApply] tryDetect() skipped — banner already injected');
    return;
  }

  const workday = isWorkday();
  const inputCount = countInputs();
  const shadowInputs = queryShadowAll<HTMLInputElement>(document.documentElement, 'input').length;
  const detectedFields = detectFields(document.documentElement);

  console.log('[simpleApply] tryDetect():', {
    isWorkday: workday,
    standardInputs: inputCount,
    shadowDOMInputs: shadowInputs,
    detectedFields: detectedFields.length,
    fieldTypes: detectedFields.map(f => `${f.fieldType}(${f.confidence})`),
    bannerInjected,
    url: window.location.href,
  });

  // Log all inputs found on the page for debugging
  if (workday) {
    const allInputs = document.querySelectorAll('input');
    console.log(`[simpleApply] All <input> elements on page: ${allInputs.length}`);
    allInputs.forEach((input, i) => {
      console.log(`[simpleApply]   input[${i}]:`, {
        type: input.type,
        name: input.name,
        id: input.id,
        'data-automation-id': input.getAttribute('data-automation-id'),
        'aria-label': input.getAttribute('aria-label'),
        placeholder: input.placeholder,
        hidden: input.type === 'hidden',
      });
    });
  }

  // Need either enough detected fields or a known platform with some inputs
  const totalInputs = Math.max(inputCount, shadowInputs);
  if (detectedFields.length < MIN_FIELDS && !(workday && totalInputs > 0)) {
    console.log('[simpleApply] Not enough fields to show banner:', {
      needed: MIN_FIELDS,
      detected: detectedFields.length,
      workdayFallback: workday && totalInputs > 0,
    });
    return;
  }

  bannerInjected = true;

  const fieldCount = workday
    ? Math.max(totalInputs, detectedFields.length)
    : detectedFields.length;
  lastFieldCount = fieldCount;

  console.log(`[simpleApply] Injecting banner with ${fieldCount} fields`);
  injectBanner(fieldCount, workday, detectedFields);
}

function injectBanner(
  fieldCount: number,
  workday: boolean,
  detectedFields: ReturnType<typeof detectFields>
): void {
  const host = document.createElement('div');
  host.id = 'simpleapply-root';
  const shadow = host.attachShadow({ mode: 'closed' });

  const style = document.createElement('style');
  style.textContent = `
    .sa-banner {
      all: initial;
      font-family: system-ui, sans-serif;
      font-size: 14px;
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 2147483647;
      background: #1a1a2e;
      color: #e0e0e0;
      border: 1px solid #4a4a6a;
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      max-width: 380px;
    }
    .sa-text { flex: 1; line-height: 1.4; }
    .sa-actions { display: flex; gap: 8px; flex-shrink: 0; }
    .sa-btn {
      all: initial;
      font-family: inherit;
      font-size: 13px;
      padding: 6px 12px;
      border-radius: 5px;
      cursor: pointer;
      border: 1px solid transparent;
      transition: background 0.15s;
    }
    .sa-accept { background: #4f46e5; color: #fff; border-color: #4f46e5; }
    .sa-accept:hover { background: #3730a3; }
    .sa-dismiss { background: transparent; color: #9ca3af; border-color: #4a4a6a; }
    .sa-dismiss:hover { background: #2d2d4e; }
  `;

  const banner = document.createElement('div');
  banner.className = 'sa-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'simpleApply auto-fill');

  const text = document.createElement('span');
  text.className = 'sa-text';
  text.textContent = `simpleApply: ${fieldCount} fields detected — Auto-fill?`;

  const actions = document.createElement('div');
  actions.className = 'sa-actions';

  const acceptBtn = document.createElement('button');
  acceptBtn.className = 'sa-btn sa-accept';
  acceptBtn.textContent = 'Auto-fill';
  acceptBtn.addEventListener('click', () => {
    banner.remove();
    doFill(workday, detectedFields);
  });

  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'sa-btn sa-dismiss';
  dismissBtn.textContent = 'Dismiss';
  dismissBtn.addEventListener('click', () => banner.remove());

  actions.appendChild(acceptBtn);
  actions.appendChild(dismissBtn);
  banner.appendChild(text);
  banner.appendChild(actions);
  shadow.appendChild(style);
  shadow.appendChild(banner);
  document.body.appendChild(host);
}

async function manualFill(): Promise<void> {
  const workday = isWorkday();
  const detectedFields = detectFields(document.documentElement);
  console.log('[simpleApply] manualFill():', {
    isWorkday: workday,
    detectedFields: detectedFields.length,
    fieldTypes: detectedFields.map(f => `${f.fieldType}(${f.confidence})`),
  });
  await doFill(workday, detectedFields);
}

async function doFill(
  workday: boolean,
  detectedFields: ReturnType<typeof detectFields>
): Promise<void> {
  try {
    const profile = await getProfile();
    if (workday) {
      await fillWorkday(profile);
    } else {
      await fillForm(document.documentElement, profile, detectedFields);
    }
  } catch (err) {
    console.error('[simpleApply] Fill failed:', err);
  }
}
