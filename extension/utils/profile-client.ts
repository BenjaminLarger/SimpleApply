export interface Experience {
  company: string;
  role: string;
  location?: string;
  start: string;          // "YYYY-MM" or "YYYY"
  end?: string;
  description?: string;
  achievements?: string[];
  technologies?: string[];
}

export interface Education {
  school: string;
  degree: string;
  fieldOfStudy?: string;
  gpa?: string;
  startYear?: string;
  endYear?: string;
}

export interface VoluntaryDisclosures {
  gender?: string;
  ethnicity?: string;
  hispanicOrLatino?: string;
  veteranStatus?: string;
  disability?: 'yes' | 'no' | 'abstain';
}

export interface ProfileData {
  name: string;
  email: string;
  phone?: string;
  phoneType?: string;     // e.g. "Mobile", "Home"
  linkedin?: string;
  github?: string;
  portfolio?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
  experiences: Experience[];
  education?: Education[];
  skills?: string[];
  resumeFilePath?: string;
  voluntaryDisclosures?: VoluntaryDisclosures;
}

const CACHE_KEY = 'simpleApply_profile';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CachedProfile {
  data: ProfileData;
  fetchedAt: number;
}

export async function getProfile(skipCache = false): Promise<ProfileData> {
  if (!skipCache) {
    // Check cache first
    const stored = await chrome.storage.local.get(CACHE_KEY);
    const cached = stored[CACHE_KEY] as CachedProfile | undefined;

    if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
      return cached.data;
    }
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
