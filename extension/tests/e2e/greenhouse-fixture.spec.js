import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FIELD_DETECTION_CODE = `
(function() {
  const FIELD_KEYWORDS = {
    firstName: ['firstname', 'first_name', 'first-name', 'givenname', 'given_name', 'given-name', 'prénom', 'prenom', 'nombre', 'vorname'],
    lastName: ['lastname', 'last_name', 'last-name', 'surname', 'familyname', 'family_name', 'nom', 'apellido', 'nachname'],
    fullName: ['fullname', 'full_name', 'full-name', 'name', 'yourname', 'nom complet', 'nombre completo'],
    email: ['email', 'e-mail', 'emailaddress', 'email_address', 'courriel', 'correo', 'correo electronico'],
    phone: ['phone', 'telephone', 'tel', 'mobile', 'cell', 'phonenumber', 'phone_number', 'téléphone', 'telefono', 'handy'],
    linkedinUrl: ['linkedin', 'linkedin_url', 'linkedinurl', 'linkedin-url', 'linkedin profile', 'profil linkedin'],
    githubUrl: ['github', 'github_url', 'githuburl', 'github-url', 'github profile'],
    portfolioUrl: ['portfolio', 'website', 'personal_website', 'personalwebsite', 'personal-website', 'site web', 'sitio web'],
    address: ['address', 'street', 'adresse', 'dirección', 'direccion', 'street_address'],
    city: ['city', 'ville', 'ciudad', 'stadt', 'locality'],
    country: ['country', 'pays', 'país', 'pais', 'land'],
    postalCode: ['postalcode', 'postal_code', 'zipcode', 'zip', 'postcode', 'code postal', 'código postal', 'codigo postal'],
    coverLetter: ['coverletter', 'cover_letter', 'cover-letter', 'lettre de motivation', 'carta de presentación', 'motivation'],
    unknown: [],
  };

  const AUTOCOMPLETE_MAP = {
    'given-name': 'firstName', 'family-name': 'lastName', 'name': 'fullName', 'email': 'email', 'tel': 'phone',
    'street-address': 'address', 'address-level2': 'city', 'country': 'country', 'postal-code': 'postalCode', 'url': 'portfolioUrl',
  };

  const PROFILE_FIELD_MAP = { email: 'email', phone: 'phone', linkedinUrl: 'linkedin', githubUrl: 'github', portfolioUrl: 'portfolio' };

  function normalise(text) { return text.toLowerCase().replace(/[\\s_\\-]/g, ''); }

  function scoreByKeywords(text) {
    const norm = normalise(text);
    for (const [type, keywords] of Object.entries(FIELD_KEYWORDS)) {
      if (type === 'unknown') continue;
      for (const kw of keywords) {
        if (norm.includes(normalise(kw))) return { type, confidence: norm === normalise(kw) ? 0.95 : 0.75 };
      }
    }
    return null;
  }

  function getLabelText(el) {
    const aria = el.getAttribute('aria-label');
    if (aria) return aria;
    const id = el.id;
    if (id) {
      const label = document.querySelector('label[for="' + id + '"]');
      if (label) return label.textContent || '';
    }
    const parentLabel = el.closest('label');
    if (parentLabel) return parentLabel.textContent || '';
    return '';
  }

  function detectFields(root) {
    const results = [];
    const inputs = Array.from(root.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea'));
    for (const el of inputs) {
      let fieldType = 'unknown', confidence = 0;
      const ac = el.getAttribute('autocomplete');
      if (ac && AUTOCOMPLETE_MAP[ac]) { fieldType = AUTOCOMPLETE_MAP[ac]; confidence = 1.0; }
      if (fieldType === 'unknown') {
        const nameVal = el.getAttribute('name') || '';
        const match = scoreByKeywords(nameVal);
        if (match && match.confidence > confidence) { fieldType = match.type; confidence = match.confidence; }
      }
      if (fieldType === 'unknown' || confidence < 0.75) {
        const idVal = el.id || '';
        const match = scoreByKeywords(idVal);
        if (match && match.confidence > confidence) { fieldType = match.type; confidence = match.confidence; }
      }
      if (fieldType === 'unknown' || confidence < 0.75) {
        const ph = el.getAttribute('placeholder') || '';
        const match = scoreByKeywords(ph);
        if (match && match.confidence > confidence) { fieldType = match.type; confidence = match.confidence * 0.85; }
      }
      if (fieldType === 'unknown' || confidence < 0.75) {
        const label = getLabelText(el);
        const match = scoreByKeywords(label);
        if (match && match.confidence > confidence) { fieldType = match.type; confidence = match.confidence * 0.9; }
      }
      if (fieldType !== 'unknown') results.push({ element: el, fieldType, confidence });
    }
    return results;
  }

  function getNamePart(profile, type) {
    const parts = (profile.name || '').split(' ');
    if (type === 'firstName') return parts[0] || '';
    if (type === 'lastName') return parts.slice(1).join(' ');
    if (type === 'fullName') return profile.name || '';
    return '';
  }

  function fillInput(el, value) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value'
    ).set;
    if (nativeInputValueSetter) nativeInputValueSetter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function fillForm(root, profile, detectedFields) {
    for (const { element, fieldType } of detectedFields) {
      let value;
      if (fieldType === 'firstName' || fieldType === 'lastName' || fieldType === 'fullName') {
        value = getNamePart(profile, fieldType);
      } else {
        const key = PROFILE_FIELD_MAP[fieldType];
        if (key) {
          const raw = profile[key];
          value = typeof raw === 'string' ? raw : undefined;
        }
      }
      if (value !== undefined) fillInput(element, value);
    }
  }

  window.testUtils = { detectFields, fillForm, FIELD_KEYWORDS, AUTOCOMPLETE_MAP };
})();
`;

const MOCK_PROFILE = {
  name: 'Alice Johnson',
  email: 'alice.johnson@example.com',
  phone: '+1 (555) 987-6543',
  linkedin: 'https://linkedin.com/in/alicejohnson',
  github: 'https://github.com/alicejohnson',
  portfolio: 'https://alicejohnson.dev',
  experiences: [],
};

test.describe('Greenhouse Application Form', () => {
  test('should detect and fill Greenhouse-style form fields', async ({ page }) => {
    const fixturePath = path.resolve(__dirname, 'fixtures/greenhouse-form.html');
    await page.goto(`file://${fixturePath}`);

    await page.addScriptTag({ content: FIELD_DETECTION_CODE });
    await page.waitForFunction(() => typeof window.testUtils !== 'undefined');

    const detectedFields = await page.evaluate(() => {
      const root = document.documentElement;
      const detected = window.testUtils.detectFields(root);
      return detected.map(field => ({
        fieldType: field.fieldType,
        confidence: field.confidence,
      }));
    });

    const fieldTypes = detectedFields.map(f => f.fieldType);
    expect(fieldTypes).toContain('firstName');
    expect(fieldTypes).toContain('lastName');
    expect(fieldTypes).toContain('email');
    expect(fieldTypes).toContain('phone');

    await page.evaluate((profile) => {
      const root = document.documentElement;
      const detected = window.testUtils.detectFields(root);
      window.testUtils.fillForm(root, profile, detected);
    }, MOCK_PROFILE);

    await expect(page.locator('#first_name')).toHaveValue('Alice');
    await expect(page.locator('#last_name')).toHaveValue('Johnson');
    await expect(page.locator('#email')).toHaveValue('alice.johnson@example.com');
    await expect(page.locator('#phone')).toHaveValue('+1 (555) 987-6543');
  });

  test('should fill LinkedIn and GitHub profile URLs', async ({ page }) => {
    const fixturePath = path.resolve(__dirname, 'fixtures/greenhouse-form.html');
    await page.goto(`file://${fixturePath}`);

    await page.addScriptTag({ content: FIELD_DETECTION_CODE });
    await page.waitForFunction(() => typeof window.testUtils !== 'undefined');

    await page.evaluate((profile) => {
      const root = document.documentElement;
      const detected = window.testUtils.detectFields(root);
      window.testUtils.fillForm(root, profile, detected);
    }, MOCK_PROFILE);

    await expect(page.locator('#linkedin_profile')).toHaveValue(
      'https://linkedin.com/in/alicejohnson'
    );
    await expect(page.locator('#github_profile')).toHaveValue('https://github.com/alicejohnson');
  });

  test('should not automatically fill resume_url with portfolio URL', async ({ page }) => {
    const fixturePath = path.resolve(__dirname, 'fixtures/greenhouse-form.html');
    await page.goto(`file://${fixturePath}`);

    await page.addScriptTag({ content: FIELD_DETECTION_CODE });
    await page.waitForFunction(() => typeof window.testUtils !== 'undefined');

    const profileWithPortfolio = {
      name: 'Bob Smith',
      email: 'bob@example.com',
      portfolio: 'https://bobsmith.com/resume.pdf',
      experiences: [],
    };

    const detectionResults = await page.evaluate((profile) => {
      const root = document.documentElement;
      const detected = window.testUtils.detectFields(root);
      window.testUtils.fillForm(root, profile, detected);
      return detected.map(f => f.fieldType);
    }, profileWithPortfolio);

    // resume_url is not detected as portfolioUrl by the field detector
    expect(detectionResults).not.toContain('portfolioUrl');
    // resume_url field should remain empty
    await expect(page.locator('#resume_url')).toHaveValue('');
  });

  test('should detect fields with high confidence using id-based identification', async ({ page }) => {
    const fixturePath = path.resolve(__dirname, 'fixtures/greenhouse-form.html');
    await page.goto(`file://${fixturePath}`);

    await page.addScriptTag({ content: FIELD_DETECTION_CODE });
    await page.waitForFunction(() => typeof window.testUtils !== 'undefined');

    const detectionResults = await page.evaluate(() => {
      const root = document.documentElement;
      const detected = window.testUtils.detectFields(root);
      return detected.map(field => ({
        fieldType: field.fieldType,
        confidence: field.confidence,
        elementId: field.element.id,
      }));
    });

    // Should detect at least 4 high-confidence fields (firstName, lastName, email, phone, etc.)
    const highConfidenceFields = detectionResults.filter(f => f.confidence >= 0.75);
    expect(highConfidenceFields.length).toBeGreaterThanOrEqual(4);
  });
});
