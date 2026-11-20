import { test, expect } from '@playwright/test';

// Feature 43 – Report form + offline (Objective 1)
// EXPECTED TO FAIL until feat/obj1/fr-form is merged.

test.describe('Reporter app – offline report submission', () => {
  test.use({
    geolocation: { latitude: 3.848, longitude: 11.502 }, // Yaoundé
    permissions: ['geolocation'],
  });

  test('report submitted offline is queued, then synced when back online', async ({ page, context }) => {
    // 1. Open the report form
    await page.goto('/report');

    // 2. Fill in the form
    await page.getByLabel('Waste type').selectOption('plastic');
    await page.getByLabel('Estimated amount').selectOption('high');
    await page.getByRole('button', { name: 'Use my location' }).click();

    // 3. Cut the network, then submit
    await context.setOffline(true);
    await page.getByRole('button', { name: 'Submit report' }).click();

    // 4. The report must be saved locally, not lost
    await expect(page.getByText(/queued/i)).toBeVisible();

    // 5. Network is back: the report must be sent automatically
    await context.setOffline(false);
    await expect(page.getByText(/synced/i)).toBeVisible({ timeout: 15_000 });
  });
});
