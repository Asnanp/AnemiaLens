import { test, expect, Page } from '@playwright/test';

async function expectScreeningSectionInView(page: Page) {
  const screeningSection = page.locator('#screening');
  await expect(screeningSection).toBeVisible();

  await expect
    .poll(
      () =>
        screeningSection.evaluate((el) => {
          const rect = el.getBoundingClientRect();
          const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
          return rect.top < viewportHeight && rect.bottom > 0;
        }),
      { timeout: 6000 },
    )
    .toBe(true);
}

async function clickViaDom(page: Page, selector: string) {
  const locator = page.locator(selector);
  await expect(locator).toBeVisible();
  await locator.evaluate((element: HTMLElement) => element.click());
}

test.describe('AnemiaLens guest screening experience', () => {
  test('Homepage loads correctly', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/AnemiaLens/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.locator('main').getByRole('button', { name: /Start Screening/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Sign In/i }).first()).toBeVisible();
  });

  test('Guest users can access screening without an auth modal', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.locator('main').getByRole('button', { name: /Start Screening/i }).first().click();

    await expectScreeningSectionInView(page);
    await expect(page.locator('#screening')).toContainText('Interactive');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });

  test('Navbar get started control scrolls the screening section into view', async ({ page }) => {
    await page.goto('/');

    const menuToggle = page.getByRole('button', { name: /Toggle menu/i });
    if (await menuToggle.isVisible()) {
      await clickViaDom(page, 'button[aria-label="Toggle menu"]');
      await clickViaDom(page, 'button.nav-mobile-cta');
    } else {
      await clickViaDom(page, 'header button.nav-primary-cta');
    }
    await expectScreeningSectionInView(page);
  });
});
