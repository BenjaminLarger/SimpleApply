<script lang="ts">
  export let fieldCount: number = 0;

  let visible = true;

  function handleAccept() {
    document.dispatchEvent(new CustomEvent('simpleApply:fill', { bubbles: true }));
    visible = false;
  }

  function handleDismiss() {
    visible = false;
  }
</script>

{#if visible}
  <div class="sa-banner" role="dialog" aria-label="simpleApply auto-fill">
    <span class="sa-text">
      simpleApply: <strong>{fieldCount}</strong> fields detected — Auto-fill?
    </span>
    <div class="sa-actions">
      <button class="sa-btn sa-accept" onclick={handleAccept}>Auto-fill</button>
      <button class="sa-btn sa-dismiss" onclick={handleDismiss}>Dismiss</button>
    </div>
  </div>
{/if}

<style>
  .sa-banner {
    all: initial;
    font-family: system-ui, sans-serif;
    font-size: 14px;
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 2147483647;
    background: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #4a4a6a;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    max-width: 380px;
  }

  .sa-text {
    flex: 1;
    line-height: 1.4;
  }

  .sa-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .sa-btn {
    all: initial;
    font-family: inherit;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 5px;
    cursor: pointer;
    border: 1px solid transparent;
    transition: background 0.15s;
  }

  .sa-accept {
    background: #4f46e5;
    color: #fff;
    border-color: #4f46e5;
  }

  .sa-accept:hover {
    background: #3730a3;
  }

  .sa-dismiss {
    background: transparent;
    color: #9ca3af;
    border-color: #4a4a6a;
  }

  .sa-dismiss:hover {
    background: #2d2d4e;
  }
</style>
