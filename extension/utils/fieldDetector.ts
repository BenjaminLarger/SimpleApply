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
  | 'password'
  | 'date'
  | 'checkbox'
  | 'unknown';

export interface DetectedField {
  element: HTMLInputElement | HTMLTextAreaElement | HTMLElement; // Also supports UI5 web components
  fieldType: FieldType;
  confidence: number; // 0–1
}

// Multilingual keyword lookup table
const FIELD_KEYWORDS: Record<FieldType, string[]> = {
  firstName: [
    'firstname', 'first_name', 'first-name', 'fname', 'f_name', 'f-name', 'givenname', 'given_name', 'given-name',
    'prénom', 'prenom', 'nombre', 'vorname',
  ],
  lastName: [
    'lastname', 'last_name', 'last-name', 'lname', 'l_name', 'l-name', 'surname', 'familyname', 'family_name',
    'nom', 'apellido', 'nachname',
  ],
  fullName: [
    'fullname', 'full_name', 'full-name', 'name', 'yourname',
    'nom complet', 'nombre completo',
  ],
  email: [
    'email', 'e-mail', 'emailaddress', 'email_address', 'username', 'user_name',
    'courriel', 'correo', 'correo electronico',
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
  password: [
    'password', 'passwd', 'pwd', 'pass', 'retype', 'confirm_password',
    'mot de passe', 'contraseña',
  ],
  date: [
    'date', 'startdate', 'start_date', 'start-date', 'enddate', 'end_date', 'end-date',
    'from_date', 'from-date', 'fromdate', 'to_date', 'todate',
    'dob', 'dateofbirth', 'date_of_birth', 'birthdate', 'birth_date',
    'date_joined', 'datejoined', 'hire_date', 'hiredate', 'joindate', 'join_date',
    'expiry_date', 'expirydate', 'expiry', 'mm/dd/yyyy', 'dd/mm/yyyy',
    'date de naissance', 'fecha de nacimiento', 'geburtsdatum',
  ],
  checkbox: [
    'agreement', 'consent', 'accept', 'agree', 'subscribe', 'notification',
    'checkbox', 'accep', 'consentement',
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
  'current-password': 'password',
  'new-password': 'password',
  password: 'password',
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
  let bestIsGeneric = false;

  // Keywords to prioritize (high-specificity fields)
  const priorityKeywords = new Set(['firstname', 'lastname', 'fname', 'lname', 'email', 'username', 'user_name', 'password', 'phone', 'linkedinurl', 'githuburl', 'portfoliourl', 'date', 'startdate', 'enddate']);
  // Generic keywords that lose to priority ones
  const genericKeywords = new Set(['name', 'address', 'city', 'country']);

  for (const [type, keywords] of Object.entries(FIELD_KEYWORDS) as [FieldType, string[]][]) {
    if (type === 'unknown') continue;
    for (const kw of keywords) {
      const normKw = normalise(kw);
      if (norm.includes(normKw)) {
        const isGeneric = genericKeywords.has(kw);
        const isPriority = priorityKeywords.has(kw);

        let confidence = norm === normKw ? 0.95 : 0.75;
        let keywordLen = normKw.length;

        // Boost priority keywords
        if (isPriority) {
          confidence = Math.min(1.0, confidence + 0.2);
          keywordLen += 100; // Virtual boost
        }

        // Skip generic keywords if we already have a priority keyword match
        if (isGeneric && bestIsGeneric === false && bestLen > 0) {
          continue;
        }

        // Prefer the longest (most specific) keyword match, but priority over generic
        const shouldUpdate = isPriority && bestIsGeneric ? true : keywordLen > bestLen;
        if (shouldUpdate) {
          best = { type, confidence };
          bestLen = keywordLen;
          bestIsGeneric = isGeneric;
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

// Expand collapsible form sections (for SuccessFactors forms with employment/education sections)
function expandFormSections(root: Element): void {
  const sectionKeywords = [
    'employment', 'experience', 'job history',
    'education', 'formal education', 'degree',
    'language', 'skills', 'mobility',
  ];

  // Find all section headers/buttons that might be collapsed
  const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>('button[class*="topBar"], button[class*="section"], h2[role="button"], h3[role="button"]'));

  let expandedCount = 0;
  for (const btn of buttons) {
    const text = btn.textContent?.toLowerCase() || '';

    // Check if this button controls a section that needs expansion
    if (sectionKeywords.some(kw => text.includes(kw))) {
      // Check if section is collapsed by looking for collapsed indicators
      const isCollapsed = btn.classList.contains('collapsed') ||
                         btn.getAttribute('aria-expanded') === 'false' ||
                         !btn.nextElementSibling?.classList.contains('expanded');

      if (isCollapsed) {
        console.log(`[simpleApply:fieldDetector] Expanding section: ${text.substring(0, 50)}`);
        btn.click();
        expandedCount++;
      }
    }
  }

  if (expandedCount > 0) {
    console.log(`[simpleApply:fieldDetector] Expanded ${expandedCount} sections`);
  }
}

// Detect UI5 date picker components (for SuccessFactors and similar SAP systems)
function detectUI5DatePickers(root: Element): DetectedField[] {
  const results: DetectedField[] = [];
  const datePickerComponents = Array.from(
    root.querySelectorAll<any>('ui5-date-picker-xweb-calendar-widget, ui5-datepicker')
  );

  if (datePickerComponents.length > 0) {
    console.log(`[simpleApply:fieldDetector] Found ${datePickerComponents.length} UI5 date picker components`);
  }

  for (const picker of datePickerComponents) {
    const title = picker.getAttribute('title') || picker.getAttribute('accessible-name') || '';
    const ariaLabel = picker.getAttribute('aria-label') || '';
    const searchText = [title, ariaLabel].join(' ').toLowerCase();

    // Check if this is a date field based on title/label
    if (searchText.includes('date') || searchText.includes('from') || searchText.includes('end') ||
        searchText.includes('start') || searchText.includes('birth')) {

      // Create a wrapper object with custom getAttribute/setAttribute to handle nested shadow DOM
      const wrappedElement = {
        ...picker,
        _actualElement: picker, // Store reference to actual DOM element for context detection
        getAttribute: (attr: string) => picker.getAttribute(attr),
        setAttribute: (attr: string, val: string) => {
          picker.setAttribute(attr, val);
          // Also set the inner input value when setAttribute is called
          if (attr === 'value' && picker.shadowRoot) {
            const ui5Input = picker.shadowRoot.querySelector<any>('ui5-input-xweb-calendar-widget');
            if (ui5Input && ui5Input.shadowRoot) {
              const innerInput = ui5Input.shadowRoot.querySelector<HTMLInputElement>('input[type="text"]');
              if (innerInput) {
                innerInput.value = val;
                innerInput.dispatchEvent(new Event('input', { bubbles: true }));
                innerInput.dispatchEvent(new Event('change', { bubbles: true }));
              }
            }
          }
        },
        tagName: picker.tagName,
        id: picker.id,
      } as any as HTMLInputElement;

      results.push({
        element: wrappedElement,
        fieldType: 'date',
        confidence: 0.95,
      });

      console.log(`[simpleApply:fieldDetector] Detected UI5 date picker: ${title || ariaLabel}`);
    }
  }

  return results;
}

export function detectFields(root: Element): DetectedField[] {
  const results: DetectedField[] = [];

  // First, expand any collapsed form sections (employment, education, etc.)
  expandFormSections(root);

  // Then, detect UI5 date picker components
  const datePickerResults = detectUI5DatePickers(root);
  results.push(...datePickerResults);

  const inputs = Array.from(root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
    'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea, input[type="password"]'
  ));
  console.log(`[simpleApply:fieldDetector] Found ${inputs.length} candidate inputs via querySelectorAll`);

  // Define detection sources in priority order
  interface DetectorConfig {
    source: string;
    getValue: (element: HTMLInputElement | HTMLTextAreaElement) => string;
    confidenceMultiplier: number;
    minConfidenceToStopSearch: number;
  }

  const detectors: DetectorConfig[] = [
    {
      source: 'autocomplete',
      getValue: (el) => {
        const ac = el.getAttribute('autocomplete');
        const acType = ac && AUTOCOMPLETE_MAP[ac];
        return acType ? `[AUTOCOMPLETE:${acType}]` : '';
      },
      confidenceMultiplier: 1.0,
      minConfidenceToStopSearch: 1.0,
    },
    {
      source: 'data-automation-id',
      getValue: (el) => el.closest('[data-automation-id]')?.getAttribute('data-automation-id') ?? '',
      confidenceMultiplier: 1.0,
      minConfidenceToStopSearch: 0.5,
    },
    {
      source: 'name',
      getValue: (el) => el.getAttribute('name') ?? '',
      confidenceMultiplier: 1.0,
      minConfidenceToStopSearch: 0.9,
    },
    {
      source: 'id',
      getValue: (el) => el.id ?? '',
      confidenceMultiplier: 1.0,
      minConfidenceToStopSearch: 0.9,
    },
    {
      source: 'placeholder',
      getValue: (el) => el.getAttribute('placeholder') ?? '',
      confidenceMultiplier: 0.85,
      minConfidenceToStopSearch: 0.75,
    },
    {
      source: 'label',
      getValue: (el) => getLabelText(el),
      confidenceMultiplier: 0.9,
      minConfidenceToStopSearch: 0.75,
    },
  ];

  for (const el of inputs) {
    // Skip fields that are sub-components (middle name, phone country code, extension)
    const sig = [el.id, el.getAttribute('name'), el.getAttribute('aria-label'),
      el.closest('[data-automation-id]')?.getAttribute('data-automation-id') ?? ''].join(' ');
    if (SKIP_PATTERNS.test(sig)) continue;

    let fieldType: FieldType = 'unknown';
    let confidence = 0;

    // Try each detector in order until we find a match above the threshold
    for (const detector of detectors) {
      // Skip if we already have high enough confidence
      if (fieldType !== 'unknown' && confidence >= detector.minConfidenceToStopSearch) {
        break;
      }

      const value = detector.getValue(el);
      if (!value) continue;

      // Special case: autocomplete with direct mapping
      if (detector.source === 'autocomplete' && value.startsWith('[AUTOCOMPLETE:')) {
        const acType = value.slice(14, -1) as FieldType;
        fieldType = acType;
        confidence = 1.0;
        break; // Highest priority — stop searching
      }

      // Standard keyword matching
      const match = scoreByKeywords(value);
      if (match && match.confidence * detector.confidenceMultiplier > confidence) {
        fieldType = match.type;
        confidence = match.confidence * detector.confidenceMultiplier;
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
