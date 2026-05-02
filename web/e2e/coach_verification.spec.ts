import { test, expect } from '@playwright/test';

test.describe('Analysis Coach Verification', () => {
  test.setTimeout(180000);

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('1. Objective-first guided flow', async ({ page }) => {
    const uniqueObjective = 'Analyze ' + Math.random().toString(36).substring(7);
    await page.fill('textarea[placeholder*="E.g., Examine"]', uniqueObjective);
    await page.click('[data-testid="start-session-btn"]');

    // Wait for the workspace to load with the unique objective
    await expect(page.getByTestId('session-objective')).toContainText(uniqueObjective, { timeout: 30000 });

    // Verify coach response
    await expect(page.getByTestId('coach-what').first()).toBeVisible({ timeout: 120000 });
  });

  test('2. Just taking a peek flow', async ({ page }) => {
    await page.click('[data-testid="peek-session-btn"]');

    await expect(page.getByTestId('session-objective')).toContainText('Quick Peek', { timeout: 30000 });

    // Wait for input to be enabled
    await expect(page.getByTestId('chat-input')).toBeEnabled({ timeout: 120000 });
    await page.getByTestId('chat-input').fill('Summarize mtcars');
    await page.getByTestId('chat-submit').click();

    // Verify peek response
    await expect(page.getByTestId('coach-what').last()).toBeVisible({ timeout: 120000 });
  });

});
