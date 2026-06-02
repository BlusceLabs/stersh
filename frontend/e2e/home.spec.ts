/**
 * Smoke tests for the home page.
 *
 * Verifies the hero carousel loads, the MediaRow components
 * render, and the basic page structure is intact.
 */
import { test, expect } from '@playwright/test';

test.describe('Home page', () => {
  test('renders the hero carousel', async ({ page }) => {
    await page.goto('/');

    const hero = page.locator('[aria-roledescription="carousel"]').first();
    await expect(hero).toBeVisible();
  });

  test('renders media rows', async ({ page }) => {
    await page.goto('/');

    // At least one MediaRow title should be visible. The exact
    // titles depend on TMDB results, so we just check for the
    // shared heading element.
    const rowHeadings = page.locator('h2, h3').filter({ hasText: /trending|popular|top rated/i });
    await expect(rowHeadings.first()).toBeVisible({ timeout: 15_000 });
  });

  test('shows the top navigation header on desktop', async ({ page }) => {
    await page.goto('/');

    const header = page.locator('header[aria-label="Primary navigation"]');
    await expect(header).toBeVisible();
  });

  test('does not show the mobile bottom nav on desktop', async ({ page }) => {
    await page.goto('/');

    const mobileNav = page.locator('nav[aria-label="Primary navigation"]');
    await expect(mobileNav).toBeHidden();
  });
});
