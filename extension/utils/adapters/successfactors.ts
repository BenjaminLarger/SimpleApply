/**
 * SuccessFactors Application Adapter
 *
 * Handles SuccessFactors-specific form filling, particularly:
 * - Language Skills (Idiomas) section with cascading picklists
 * - Spanish locale support
 */

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

export function isSuccessFactors(): boolean {
  // Check URL first
  if (/successfactors\.com|successfactors\.eu/i.test(window.location.hostname)) {
    console.log('[simpleApply:sf] isSuccessFactors=true (URL)');
    return true;
  }

  // Check DOM for SuccessFactors-specific elements
  const dom = !![
    '[role="group"][aria-labelledby]', // SF section structure
    'input.rcmpaginatedselectinput', // SF cascading picklist
    '[class*="rcm"]', // SF SAP UI5 components
  ].some(selector => document.querySelector(selector));

  if (dom) {
    console.log('[simpleApply:sf] isSuccessFactors=true (DOM)');
  } else {
    console.log('[simpleApply:sf] isSuccessFactors=false (DOM)');
  }

  return dom;
}
