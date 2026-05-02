import { test, expect } from '@playwright/test';

test('MVP Vertical Slice Flow', async ({ page }) => {
  await page.goto('/');
  
  // Onboarding
  await page.fill('textarea[placeholder*="E.g., Examine"]', 'Verify MVP Flow');
  await page.click('button:has-text("START SESSION")');

  // Verify Workspace transition (Increase timeout for Cloud Run cold starts)
  await expect(page.getByTestId('chat-input')).toBeVisible({ timeout: 60000 });

  // Verify Workspace header
  await expect(page.getByTestId('session-objective')).toContainText('Verify MVP Flow');
});
