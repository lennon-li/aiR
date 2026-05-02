import { test, expect } from '@playwright/test';

test('Snapshot: Verify Setup and Workspace Orientation', async ({ page }) => {
  await page.goto('/');
  
  // Verify onboarding landing
  await expect(page.locator('h1')).toContainText('aiR');
  
  // Go to workspace
  await page.click('button:has-text("I’m just taking a peek")');
  
  // Verify workspace structure
  await expect(page.getByTestId('session-objective')).toBeVisible({ timeout: 15000 });
});
