import type { ProfileData } from '../utils/profile-client.js';

const PROFILE_CACHE_KEY = 'simpleApply_profile';
const ALARM_NAME = 'simpleApply_profile_refresh';
const API_URL = 'http://localhost:8765/api/profile';

export default defineBackground(() => {
  // Fetch and cache on install
  chrome.runtime.onInstalled.addListener(() => {
    fetchAndCacheProfile();
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: 24 * 60 });
  });

  // Refresh on daily alarm
  chrome.alarms.onAlarm.addListener((alarm: chrome.alarms.Alarm) => {
    if (alarm.name === ALARM_NAME) {
      fetchAndCacheProfile();
    }
  });

  // Respond to messages requesting profile
  chrome.runtime.onMessage.addListener((
    message: { type?: string },
    _sender: chrome.runtime.MessageSender,
    sendResponse: (response: unknown) => void
  ): boolean | undefined => {
    if (message?.type === 'GET_PROFILE') {
      chrome.storage.local.get(PROFILE_CACHE_KEY).then((stored: Record<string, unknown>) => {
        sendResponse({ profile: stored[PROFILE_CACHE_KEY] ?? null });
      });
      return true; // keep channel open for async response
    }
    return undefined;
  });
});

async function fetchAndCacheProfile(): Promise<void> {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) return;
    const data: ProfileData = await response.json() as ProfileData;
    await chrome.storage.local.set({
      [PROFILE_CACHE_KEY]: { data, fetchedAt: Date.now() },
    });
  } catch {
    // Server may not be running — silently skip
  }
}
