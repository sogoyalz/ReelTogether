import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests',
  workers: 1,
  globalTimeout: 180_000,
  reporter: 'line',
  use: { baseURL: 'http://127.0.0.1:3011', timezoneId: 'America/Chicago', trace: 'retain-on-failure' },
  webServer: [
    { command: `${process.env.BACKEND_PYTHON || '../backend/venv/bin/python'} ../backend/tests/serve_e2e.py`, url: 'http://127.0.0.1:8011/health/live', stdout: 'pipe', reuseExistingServer: false },
    { command: 'npm run dev -- --port 3011', url: 'http://127.0.0.1:3011', env: { PROXY_SHARED_SECRET: 'test-only-browser-proxy-secret', API_BASE_URL: 'http://127.0.0.1:8011', NEXT_TELEMETRY_DISABLED: '1' }, timeout: 120000, stdout: 'pipe', reuseExistingServer: false },
  ],
})
