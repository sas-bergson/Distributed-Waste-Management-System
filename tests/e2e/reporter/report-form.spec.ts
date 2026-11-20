import { test, expect } from '@playwright/test';

// Feature 43 – Report form validation (Objective 1)
// EXPECTED TO FAIL until feat/obj1/fr-form is merged.

test.describe('Reporter app – report form validation', () => {
  test.use({
    geolocation: { latitude: 3.848, longitude: 11.502 }, // Yaoundé
    permissions: ['geolocation'],
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/report');
  });

  test('empty form cannot be submitted', async ({ page }) => {
    await page.getByRole('button', { name: 'Submit report' }).click();
    await expect(page.getByText(/waste type is required/i)).toBeVisible();
    await expect(page.getByText(/location is required/i)).toBeVisible();
  });

  test('invalid GPS coordinates are rejected', async ({ page }) => {
    await page.getByLabel('Waste type').selectOption('plastic');
    await page.getByLabel('Estimated amount').selectOption('low');
    await page.getByLabel('Latitude').fill('200'); // impossible: max is 90
    await page.getByLabel('Longitude').fill('11.502');
    await page.getByRole('button', { name: 'Submit report' }).click();
    await expect(page.getByText(/invalid coordinates/i)).toBeVisible();
  });

  test('valid report is submitted successfully online', async ({ page }) => {
    await page.getByLabel('Waste type').selectOption('organic');
    await page.getByLabel('Estimated amount').selectOption('moderate');
    await page.getByRole('button', { name: 'Use my location' }).click();
    await page.getByRole('button', { name: 'Submit report' }).click();
    await expect(page.getByText(/report submitted/i)).toBeVisible();
  });
});
