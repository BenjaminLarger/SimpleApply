import { defineBackground } from 'wxt/sandbox';
import { browser } from 'wxt/browser';
import type { ProfileData } from '../utils/profile-client.js';

const PROFILE_CACHE_KEY = 'simpleApply_profile';
const API_URL = 'http://localhost:8765/api/profile';

export default defineBackground(() => {
  // Fetch and cache on install
  browser.runtime.onInstalled.addListener(() => {
    fetchAndCacheProfile();
  });

  // Respond to messages requesting profile
  browser.runtime.onMessage.addListener((
    message: { type?: string },
    _sender,
    sendResponse: (response: unknown) => void
  ): boolean | undefined => {
    if (message?.type === 'GET_PROFILE') {
      browser.storage.local.get(PROFILE_CACHE_KEY).then((stored: Record<string, unknown>) => {
        sendResponse({ profile: stored[PROFILE_CACHE_KEY] ?? null });
      });
      return true;
    }
    return undefined;
  });
});

async function fetchAndCacheProfile(): Promise<void> {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) return;
    const data: ProfileData = await response.json() as ProfileData;
    await browser.storage.local.set({
      [PROFILE_CACHE_KEY]: { data, fetchedAt: Date.now() },
    });
  } catch {
    // Server may not be running — silently skip
  }
}
