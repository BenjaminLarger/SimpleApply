export type FieldType =
  | 'firstName'
  | 'lastName'
  | 'fullName'
  | 'email'
  | 'phone'
  | 'linkedinUrl'
  | 'githubUrl'
  | 'portfolioUrl'
  | 'address'
  | 'city'
  | 'country'
  | 'postalCode'
  | 'coverLetter'
  | 'unknown';

export interface DetectedField {
  element: HTMLInputElement | HTMLTextAreaElement;
  fieldType: FieldType;
  confidence: number; // 0–1
}

// Multilingual keyword lookup table
const FIELD_KEYWORDS: Record<FieldType, string[]> = {
  firstName: [
    'firstname', 'first_name', 'first-name', 'givenname', 'given_name', 'given-name',
    'prénom', 'prenom', 'nombre', 'vorname',
  ],
  lastName: [
    'lastname', 'last_name', 'last-name', 'surname', 'familyname', 'family_name',
    'nom', 'apellido', 'nachname',
  ],
  fullName: [
    'fullname', 'full_name', 'full-name', 'name', 'yourname',
    'nom complet', 'nombre completo',
  ],
  email: [
    'email', 'e-mail', 'emailaddress', 'email_address', 'courriel',
    'correo', 'correo electronico',
  ],
  phone: [
    'phone', 'telephone', 'tel', 'mobile', 'cell', 'phonenumber', 'phone_number',
    'téléphone', 'telefono', 'handy',
  ],
  linkedinUrl: [
    'linkedin', 'linkedin_url', 'linkedinurl', 'linkedin-url', 'linkedin profile',
    'profil linkedin',
  ],
  githubUrl: [
    'github', 'github_url', 'githuburl', 'github-url', 'github profile',
  ],
  portfolioUrl: [
    'portfolio', 'website', 'personal_website', 'personalwebsite', 'personal-website',
    'site web', 'sitio web',
  ],
  address: [
    'address', 'street', 'adresse', 'dirección', 'direccion', 'street_address',
  ],
  city: [
    'city', 'ville', 'ciudad', 'stadt', 'locality',
  ],
  country: [
    'country', 'pays', 'país', 'pais', 'land',
  ],
  postalCode: [
    'postalcode', 'postal_code', 'zipcode', 'zip', 'postcode',
    'code postal', 'código postal', 'codigo postal',
  ],
  coverLetter: [
    'coverletter', 'cover_letter', 'cover-letter', 'lettre de motivation',
    'carta de presentación', 'motivation',
  ],
  unknown: [],
};

// Autocomplete attribute mapping
const AUTOCOMPLETE_MAP: Partial<Record<string, FieldType>> = {
  'given-name': 'firstName',
  'family-name': 'lastName',
  name: 'fullName',
  email: 'email',
  tel: 'phone',
  'street-address': 'address',
  'address-level2': 'city',
  country: 'country',
  'postal-code': 'postalCode',
  url: 'portfolioUrl',
};

// Patterns that should NOT be matched (sub-fields we don't fill)
const SKIP_PATTERNS = /middle.?name|secondary.?last.?name|country.?phone.?code|phone.?extension|phone.?ext(?:ension)?$/i;

function normalise(text: string): string {
  return text.toLowerCase().replace(/[\s_\-]/g, '');
}

function scoreByKeywords(text: string): { type: FieldType; confidence: number } | null {
  // Split compound identifiers (e.g. "address--city", "addressSection_postalCode")
  // and try the last segment first — it's typically the most specific part
  const segments = text.split(/--|__|_|-/).filter(Boolean);
  const lastSegment = segments.length > 1 ? segments[segments.length - 1] : null;

  if (lastSegment) {
    const lastMatch = matchKeywords(lastSegment);
    if (lastMatch) return lastMatch;
  }

  return matchKeywords(text);
}

function matchKeywords(text: string): { type: FieldType; confidence: number } | null {
  const norm = normalise(text);
  let best: { type: FieldType; confidence: number } | null = null;
  let bestLen = 0;

  for (const [type, keywords] of Object.entries(FIELD_KEYWORDS) as [FieldType, string[]][]) {
    if (type === 'unknown') continue;
    for (const kw of keywords) {
      const normKw = normalise(kw);
      if (norm.includes(normKw)) {
        const confidence = norm === normKw ? 0.95 : 0.75;
        // Prefer the longest (most specific) keyword match
        if (normKw.length > bestLen) {
          best = { type, confidence };
          bestLen = normKw.length;
        }
      }
    }
  }
  return best;
}

function getLabelText(el: HTMLInputElement | HTMLTextAreaElement): string {
  const aria = el.getAttribute('aria-label');
  if (aria) return aria;

  const id = el.id;
  if (id) {
    const label = el.ownerDocument.querySelector<HTMLLabelElement>(`label[for="${id}"]`);
    if (label) return label.textContent ?? '';
  }

  const parentLabel = el.closest('label');
  if (parentLabel) return parentLabel.textContent ?? '';

  return '';
}

export function detectFields(root: Element): DetectedField[] {
  const results: DetectedField[] = [];
  const inputs = Array.from(root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
    'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea'
  ));
  console.log(`[simpleApply:fieldDetector] Found ${inputs.length} candidate inputs via querySelectorAll`);

  for (const el of inputs) {
    // Skip fields that are sub-components (middle name, phone country code, extension)
    const sig = [el.id, el.getAttribute('name'), el.getAttribute('aria-label'),
      el.closest('[data-automation-id]')?.getAttribute('data-automation-id') ?? ''].join(' ');
    if (SKIP_PATTERNS.test(sig)) continue;

    let fieldType: FieldType = 'unknown';
    let confidence = 0;

    // 1. autocomplete attribute (highest priority)
    const ac = el.getAttribute('autocomplete');
    if (ac && AUTOCOMPLETE_MAP[ac]) {
      fieldType = AUTOCOMPLETE_MAP[ac]!;
      confidence = 1.0;
    }

    // 2. data-automation-id (Workday) — low-priority hint from parent container
    if (fieldType === 'unknown') {
      const autoId = el.closest('[data-automation-id]')?.getAttribute('data-automation-id') ?? '';
      const match = scoreByKeywords(autoId);
      if (match && match.confidence > confidence) {
        fieldType = match.type;
        // Mark as tentative (0.5) so element-level signals can override
        confidence = 0.5;
      }
    }

    // 3. name attribute
    if (fieldType === 'unknown' || confidence < 0.9) {
      const nameVal = el.getAttribute('name') ?? '';
      const match = scoreByKeywords(nameVal);
      if (match && match.confidence > confidence) {
        fieldType = match.type;
        confidence = match.confidence;
      }
    }

    // 4. id attribute
    if (fieldType === 'unknown' || confidence < 0.9) {
      const idVal = el.id ?? '';
      const match = scoreByKeywords(idVal);
      if (match && match.confidence > confidence) {
        fieldType = match.type;
        confidence = match.confidence;
      }
    }

    // 5. placeholder
    if (fieldType === 'unknown' || confidence < 0.75) {
      const ph = el.getAttribute('placeholder') ?? '';
      const match = scoreByKeywords(ph);
      if (match && match.confidence > confidence) {
        fieldType = match.type;
        confidence = match.confidence * 0.85;
      }
    }

    // 6. label text
    if (fieldType === 'unknown' || confidence < 0.75) {
      const label = getLabelText(el);
      const match = scoreByKeywords(label);
      if (match && match.confidence > confidence) {
        fieldType = match.type;
        confidence = match.confidence * 0.9;
      }
    }

    // Reject matches on inputs with no id, no name, and no autocomplete — these are
    // typically framework-generated helper inputs (e.g. Workday combobox search triggers)
    const hasDirectAttr = !!(el.id || el.getAttribute('name') || el.getAttribute('autocomplete')
      || el.getAttribute('placeholder'));
    if (fieldType !== 'unknown' && hasDirectAttr) {
      console.log(`[simpleApply:fieldDetector] Matched: ${fieldType} (${confidence}) ←`, {
        name: el.getAttribute('name'),
        id: el.id,
        'aria-label': el.getAttribute('aria-label'),
        'data-automation-id': el.getAttribute('data-automation-id'),
      });
      results.push({ element: el, fieldType, confidence });
    }
  }

  console.log(`[simpleApply:fieldDetector] Total matched: ${results.length}/${inputs.length}`);
  return results;
}
