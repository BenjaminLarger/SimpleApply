const RESUME_STORAGE_KEY = 'simpleApply_resume';

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const statusEl = document.getElementById('status');
const currentResumeEl = document.getElementById('currentResume');
const resumeNameEl = document.getElementById('resumeName');
const resumeSizeEl = document.getElementById('resumeSize');
const removeBtn = document.getElementById('removeBtn');

// Load existing resume info
loadResumeInfo();

// Click to upload
uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  if (file) handleFile(file);
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadArea.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', () => {
  uploadArea.classList.remove('dragover');
});
uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.classList.remove('dragover');
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFile(file);
});

// Remove
removeBtn.addEventListener('click', async () => {
  await chrome.storage.local.remove(RESUME_STORAGE_KEY);
  currentResumeEl.style.display = 'none';
  showStatus('Resume removed', 'success');
});

async function loadResumeInfo() {
  const stored = await chrome.storage.local.get(RESUME_STORAGE_KEY);
  const resume = stored[RESUME_STORAGE_KEY];
  if (resume?.fileName) {
    resumeNameEl.textContent = resume.fileName;
    // Estimate size from base64 length
    const sizeBytes = Math.round((resume.fileData?.length ?? 0) * 0.75);
    resumeSizeEl.textContent = formatSize(sizeBytes);
    currentResumeEl.style.display = 'flex';
  }
}

async function handleFile(file) {
  // Validate type
  const validTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ];
  if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx)$/i)) {
    showStatus('Please upload a PDF, DOC, or DOCX file', 'error');
    return;
  }

  // Validate size (10MB max for chrome.storage.local)
  if (file.size > 8 * 1024 * 1024) {
    showStatus('File too large — max 8MB', 'error');
    return;
  }

  showStatus('Storing resume...', 'uploading');

  try {
    const base64 = await fileToBase64(file);

    await chrome.storage.local.set({
      [RESUME_STORAGE_KEY]: {
        fileData: base64,
        fileName: file.name,
        contentType: file.type || 'application/pdf',
      },
    });

    resumeNameEl.textContent = file.name;
    resumeSizeEl.textContent = formatSize(file.size);
    currentResumeEl.style.display = 'flex';
    showStatus('Resume saved successfully!', 'success');
  } catch (err) {
    console.error('Failed to store resume:', err);
    showStatus('Failed to store resume: ' + err.message, 'error');
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      resolve(dataUrl.split(',')[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = 'status ' + type;
  if (type === 'success') {
    setTimeout(() => { statusEl.className = 'status'; }, 3000);
  }
}
