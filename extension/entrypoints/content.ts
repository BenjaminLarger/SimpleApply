import { detectFields } from '../utils/fieldDetector.js';
import { queryShadowAll } from '../utils/shadowDom.js';
import { fillForm } from '../utils/dynamicFiller.js';
import { getProfile } from '../utils/profile-client.js';
import AutofillBanner from '../components/AutofillBanner.svelte';

const MIN_FIELDS = 3;

export default defineContentScript({
  matches: ['<all_urls>'],
  async main() {
    document.addEventListener('DOMContentLoaded', init);
    // Also run if DOMContentLoaded already fired
    if (document.readyState !== 'loading') {
      init();
    }
  },
});

function init(): void {
  const allInputs = queryShadowAll<HTMLInputElement | HTMLTextAreaElement>(
    document.documentElement,
    'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea'
  );

  if (allInputs.length === 0) return;

  const detectedFields = detectFields(document.documentElement);
  if (detectedFields.length < MIN_FIELDS) return;

  // Inject the banner into a shadow host so styles don't leak
  const host = document.createElement('div');
  host.id = 'simpleapply-root';
  document.body.appendChild(host);

  const banner = new AutofillBanner({
    target: host,
    props: { fieldCount: detectedFields.length },
  });

  // Listen for fill event dispatched by the banner
  document.addEventListener('simpleApply:fill', async () => {
    try {
      const profile = await getProfile();
      await fillForm(document.documentElement, profile, detectedFields);
    } catch (err) {
      console.error('[simpleApply] Fill failed:', err);
    }
  });
}
