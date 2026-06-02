/**
 * Search page tests: keyboard, debounce, empty state.
 */
import { test, expect } from '@playwright/test';

test.describe('Search', () => {
  test('renders the search input', async ({ page }) => {
    await page.goto('/search');

    const input = page.locator('input[type="search"], input[type="text"]').first();
    await expect(input).toBeVisible();
  });

  test('shows an empty state when there are no results', async ({ page }) => {
    await page.goto('/search');

    const input = page.locator('input[type="search"], input[type="text"]').first();
    await input.fill('zzzzzzzzz-no-such-movie-zzzzzzzzz');

    // The search debounces for 350ms before firing.
    await page.waitForTimeout(800);

    // Either the empty-state element appears, or a "no results" message.
    const emptyState = page.locator('[role="status"]');
    await expect(emptyState.first()).toBeVisible({ timeout: 5_000 });
  });

  test('clearing the input does not crash', async ({ page }) => {
    await page.goto('/search');

    const input = page.locator('input[type="search"], input[type="text"]').first();
    await input.fill('inception');
    await page.waitForTimeout(500);
    await input.fill('');
    await page.waitForTimeout(500);

    // Page should still be interactive.
    await expect(input).toBeVisible();
  });
});
