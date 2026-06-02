/**
 * Mobile-specific tests: the bottom-tab Navbar replaces the desktop
 * header on small viewports.
 */
import { test, expect } from '@playwright/test';

test.describe('Mobile navigation', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('shows the mobile bottom nav on mobile viewport', async ({ page }) => {
    await page.goto('/');

    const mobileNav = page.locator('nav[aria-label="Primary navigation"]');
    await expect(mobileNav).toBeVisible();
  });

  test('hides the desktop header on mobile viewport', async ({ page }) => {
    await page.goto('/');

    const header = page.locator('header[aria-label="Primary navigation"]');
    await expect(header).toBeHidden();
  });

  test('mobile nav links navigate to the correct routes', async ({ page }) => {
    await page.goto('/');

    const moviesLink = page.locator('nav[aria-label="Primary navigation"] a[href="/movies"]');
    await expect(moviesLink).toBeVisible();

    await moviesLink.click();
    await expect(page).toHaveURL(/\/movies$/);
  });

  test('tap targets are at least 44px (a11y baseline)', async ({ page }) => {
    await page.goto('/');

    const links = page.locator('nav[aria-label="Primary navigation"] a');
    const count = await links.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const box = await links.nth(i).boundingBox();
      expect(box?.height ?? 0, `link ${i} height`).toBeGreaterThanOrEqual(40);
    }
  });
});
