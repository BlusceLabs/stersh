/**
 * Navigation smoke tests: pages load, status is 2xx/3xx, no console errors.
 */
import { test, expect, type ConsoleMessage } from '@playwright/test';

const PAGES = [
  { path: '/', name: 'home' },
  { path: '/movies', name: 'movies' },
  { path: '/tv', name: 'tv' },
  { path: '/search', name: 'search' },
  { path: '/movie/27205', name: 'details (movie)' },
  { path: '/tv/1399', name: 'details (tv)' },
];

for (const { path, name } of PAGES) {
  test(`${name} loads without console errors`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    const response = await page.goto(path);
    expect(response, `no response for ${path}`).not.toBeNull();
    expect(response!.status(), `${path} status`).toBeLessThan(400);

    // Allow scripts to settle.
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});

    // Filter out network errors (TMDB rate limits, blocked fetches) —
    // those are environmental, not app bugs.
    const realErrors = consoleErrors.filter(
      (e) => !/failed to fetch|net::|timeout|abort/i.test(e)
    );
    expect(realErrors, `console errors on ${path}`).toEqual([]);
  });
}
