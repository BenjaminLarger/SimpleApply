export interface Experience {
  company: string;
  role: string;
  start: string;
  end?: string;
  achievements?: string[];
  technologies?: string[];
}

export interface ProfileData {
  name: string;
  email: string;
  phone?: string;
  linkedin?: string;
  github?: string;
  portfolio?: string;
  address?: string;
  city?: string;
  postalCode?: string;
  country?: string;
  experiences: Experience[];
}

const CACHE_KEY = 'simpleApply_profile';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CachedProfile {
  data: ProfileData;
  fetchedAt: number;
}

export async function getProfile(): Promise<ProfileData> {
  // Check cache first
  const stored = await chrome.storage.local.get(CACHE_KEY);
  const cached = stored[CACHE_KEY] as CachedProfile | undefined;

  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.data;
  }

  // Fetch from local API server
  const response = await fetch('http://localhost:8765/api/profile');
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }

  const data: ProfileData = await response.json();

  // Store in cache
  const entry: CachedProfile = { data, fetchedAt: Date.now() };
  await chrome.storage.local.set({ [CACHE_KEY]: entry });

  return data;
}
