<script lang="ts">
  import { onMount } from 'svelte';

  let connected = false;
  let enabled = true;
  let fieldCount = 0;
  let statusMessage = 'Checking…';

  onMount(async () => {
    await checkApiStatus();
    await getFieldCount();
  });

  async function checkApiStatus() {
    try {
      const res = await fetch('http://localhost:8765/api/health');
      connected = res.ok;
      statusMessage = connected ? 'Connected' : 'Disconnected';
    } catch {
      connected = false;
      statusMessage = 'Disconnected';
    }
  }

  async function getFieldCount() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;

    chrome.tabs.sendMessage(tab.id, { type: 'GET_FIELD_COUNT' }, (response) => {
      if (chrome.runtime.lastError) return;
      fieldCount = response?.count ?? 0;
    });
  }

  function handleToggle() {
    enabled = !enabled;
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, { type: 'SET_ENABLED', enabled });
      }
    });
  }

  function handleManualFill() {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, { type: 'MANUAL_FILL' });
      }
    });
  }
</script>

<main>
  <header>
    <h1>simpleApply</h1>
  </header>

  <section class="status">
    <span class="label">API Server</span>
    <span class="badge {connected ? 'ok' : 'err'}">
      {statusMessage}
    </span>
  </section>

  <section class="fields">
    <span class="label">Fields detected</span>
    <span class="value">{fieldCount}</span>
  </section>

  <section class="toggle-row">
    <label>
      <input type="checkbox" bind:checked={enabled} onchange={handleToggle} />
      Enable auto-fill
    </label>
  </section>

  <button class="fill-btn" onclick={handleManualFill} disabled={!connected}>
    Manual Fill
  </button>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
    width: 280px;
  }

  main {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  h1 {
    font-size: 18px;
    margin: 0;
    color: #a5b4fc;
  }

  .status,
  .fields {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
  }

  .label {
    color: #9ca3af;
  }

  .value {
    font-weight: bold;
  }

  .badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 9999px;
    font-weight: 600;
  }

  .badge.ok {
    background: #065f46;
    color: #6ee7b7;
  }

  .badge.err {
    background: #7f1d1d;
    color: #fca5a5;
  }

  .toggle-row label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    cursor: pointer;
  }

  .fill-btn {
    padding: 8px;
    background: #4f46e5;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .fill-btn:hover:not(:disabled) {
    background: #3730a3;
  }

  .fill-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>
