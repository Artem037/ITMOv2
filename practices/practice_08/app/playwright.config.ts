import { defineConfig } from '@playwright/test';

const baseURL = 'http://127.0.0.1:5174';

export default defineConfig({
  testDir: './tests',
  use: { baseURL },
  webServer: {
    command: 'npm run dev -- --strictPort --port 5174',
    url: baseURL,
  },
});
