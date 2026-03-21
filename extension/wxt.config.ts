import { defineConfig } from 'wxt';

export default defineConfig({
  modules: ['@wxt-dev/module-svelte'],
  manifest: {
    name: 'simpleApply',
    version: '0.1.0',
    description: 'Auto-fill job application forms using your saved profile.',
    host_permissions: [
      'http://localhost:8765/*',
      '*://*.linkedin.com/*',
      '*://*.greenhouse.io/*',
      '*://*.lever.co/*',
      '*://*.myworkdayjobs.com/*',
      '*://*.smartrecruiters.com/*',
    ],
  },
});
