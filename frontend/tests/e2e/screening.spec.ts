import { test, expect } from '@playwright/test';

test.describe('AnemiaLens Phase 3 e2e Suite', () => {

  test('Homepage loads correctly', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/AnemiaLens/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.getByText('Get Started')).toBeVisible();
  });

  test('Authentication modal works', async ({ page }) => {
    await page.goto('/');
    await page.getByText('Sign In').click();
    
    // Expect the modal to show Welcome Back or Create Account
    await expect(page.locator('text=Welcome back').or(page.locator('text=Create account'))).toBeVisible();

    // Toggle to Register mode
    await page.getByRole('button', { name: 'SIGN UP' }).click();
    await expect(page.getByPlaceholder('Full name (optional)')).toBeVisible();

    // Close the modal
    await page.getByRole('button', { name: 'Continue without account' }).click();
  });

  test('Navbar scrolls screening section into view', async ({ page }) => {
    await page.goto('/');
    
    // Wait for animation to finish
    await page.waitForTimeout(1000);

    // Get started button in the nav panel
    const getStartedBtn = page.locator('.nav-desktop >> text=Get Started');
    await getStartedBtn.click();

    // Wait for the scrolling logic (which is slightly delayed 150ms in code)
    await page.waitForTimeout(500);

    // Check if screening section is in viewport
    const screeningSection = page.locator('#screening');
    await expect(screeningSection).toBeInViewport();
  });
});
