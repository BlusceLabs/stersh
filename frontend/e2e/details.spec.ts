/**
 * Details page tests.
 */
import { test, expect } from '@playwright/test';

test.describe('Details page', () => {
  test('renders the title, metadata, and play button', async ({ page }) => {
    await page.goto('/movie/27205');

    // Movie title (Inception, 2010)
    const title = page.getByRole('heading', { level: 1 });
    await expect(title).toBeVisible({ timeout: 15_000 });

    // Play button is part of the HeroCarousel/details block.
    const playButton = page.getByRole('link', { name: /play|watch/i }).first();
    await expect(playButton).toBeVisible();
  });

  test('renders the Recommendations row', async ({ page }) => {
    await page.goto('/movie/27205');

    const recs = page.getByText(/recommendations/i).first();
    await expect(recs).toBeVisible({ timeout: 15_000 });
  });

  test('TV details page renders the season selector', async ({ page }) => {
    await page.goto('/tv/1399');

    // For TV, the DetailsPage shows a season selector.
    const seasonSelect = page.locator('select, [role="combobox"]').first();
    await expect(seasonSelect).toBeVisible({ timeout: 15_000 });
  });
});
