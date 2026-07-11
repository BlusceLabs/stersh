import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Stersh end-to-end tests.
 *
 * Tests are co-located under `e2e/`. By default they expect the dev
 * server to be running on http://localhost:4321 (use `npm run dev`
 * in another terminal, or `npm run preview` after a build).
 *
 * `webServer` will auto-start `npm run dev` if no server is
 * reachable on 4321 — disable this with `PLAYWRIGHT_SKIP_WEBSERVER=1`
 * to run against a remote deployment.
 */
export default defineConfig({
  testDir: './e2e',

  // Tight timeouts for fast feedback; bumping to 30s in CI for
  // cold-start jitter.
  timeout: process.env.CI ? 30_000 : 10_000,
  expect: { timeout: 5_000 },

  // Re-run failed tests in CI; never locally (keeps dev loop fast).
  retries: process.env.CI ? 1 : 0,

  // Don't run tests in parallel by default — they share the
  // TMDB rate-limit budget and the dev server. Flip to true
  // when running against a staging environment.
  fullyParallel: false,
  workers: 1,

  // Single reporter for dev, line reporter for CI logs.
  reporter: process.env.CI ? 'line' : 'list',

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:4321',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'chromium-mobile',
      use: { ...devices['Pixel 7'] },
    },
  ],

  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:4321',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        stdout: 'ignore',
        stderr: 'pipe',
      },
});
