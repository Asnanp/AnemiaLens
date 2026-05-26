import { test, expect, Page, Locator } from '@playwright/test';

async function expectScreeningSectionInView(page: Page) {
  const screeningSection = page.locator('#screening');
  await expect(screeningSection).toBeVisible();
  await screeningSection.scrollIntoViewIfNeeded();
}

async function clickViaDom(page: Page, selectorOrLocator: string | Locator) {
  const locator = typeof selectorOrLocator === 'string' ? page.locator(selectorOrLocator) : selectorOrLocator;
  await expect(locator).toBeVisible();
  await locator.evaluate((element: HTMLElement) => element.click());
}

test.describe('AnemiaLens guest screening experience', () => {
  test.beforeEach(async ({ context }) => {
    // Set onboarding as complete so it doesn't show up in tests
    await context.addInitScript(() => {
      window.localStorage.setItem('anemialens.onboarding-complete', JSON.stringify({
        complete: true,
        version: 1,
        completedAt: Date.now()
      }));
    });
  });

  test('Homepage loads correctly', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/AnemiaLens/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.locator('main').getByRole('button', { name: /Start Screening/i }).first()).toBeVisible();
    
    // Check Sign In visibility based on viewport/hamburger menu visibility
    const menuToggle = page.getByRole('button', { name: /Toggle menu/i });
    if (await menuToggle.isVisible()) {
      await expect(menuToggle).toBeVisible();
    } else {
      await expect(page.getByRole('button', { name: /Sign In/i }).first()).toBeVisible();
    }
  });

  test('Guest users can access screening without an auth modal', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('dialog')).toHaveCount(0);
    await clickViaDom(page, page.locator('main').getByRole('button', { name: /Start Screening/i }).first());

    await expectScreeningSectionInView(page);
    await expect(page.locator('#screening')).toContainText('Guided Screening');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });

  test('Navbar get started control scrolls the screening section into view', async ({ page }) => {
    await page.goto('/');

    const menuToggle = page.getByRole('button', { name: /Toggle menu/i });
    if (await menuToggle.isVisible()) {
      await clickViaDom(page, 'button[aria-label="Toggle menu"]');
      await clickViaDom(page, 'button.nav-mobile-cta');
    } else {
      await clickViaDom(page, 'header a.nav-primary-cta');
    }
    await expectScreeningSectionInView(page);
  });

  test('Full screening workflow using demo cases', async ({ page }) => {
    // Increase test timeout for this heavy end-to-end clinical inference pipeline
    test.setTimeout(60000);

    await page.goto('/');

    // 1. Go to screening section
    await clickViaDom(page, page.locator('main').getByRole('button', { name: /Start Screening/i }).first());
    await expectScreeningSectionInView(page);

    // 2. Click on the first demo card to load it
    const demoCard = page.locator('.screening-demo-card').first();
    await clickViaDom(page, demoCard);

    // 3. Click Validate Quality button (wait up to 15s for the sample image fetch to complete)
    const validateBtn = page.getByRole('button', { name: /Run image quality validation/i });
    await expect(validateBtn).toBeVisible({ timeout: 15000 });
    await clickViaDom(page, validateBtn);

    // 4. Click Continue in the Quality View (wait up to 20s for the quality check to finish)
    const continueBtn = page.getByRole('button', { name: /Continue/i });
    await expect(continueBtn).toBeVisible({ timeout: 20000 });
    await clickViaDom(page, continueBtn);

    // 5. Click Run Clinical Workflow in the Intake View (wait up to 15s)
    const runBtn = page.getByRole('button', { name: /Run Clinical Workflow/i });
    await expect(runBtn).toBeVisible({ timeout: 15000 });
    await clickViaDom(page, runBtn);

    // 6. We should see the results page with PDF Report button (wait up to 25s for the full LLM and clinical inference pipeline)
    const exportBtn = page.getByRole('button', { name: /PDF Report/i });
    await expect(exportBtn).toBeVisible({ timeout: 25000 });
  });
});
