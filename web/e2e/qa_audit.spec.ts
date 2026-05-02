import { test, expect } from '@playwright/test';

test('QA Audit: Full MVP Workflow', async ({ page }) => {
  page.on('dialog', d => { console.log(`ALERT: ${d.message()}`); d.dismiss().catch(()=>{}); });
  page.on('console', m => { console.log(`BROWSER: ${m.text()}`); });

  await page.goto('/');
  
  // 1. Landing Check
  await expect(page.locator('h1')).toContainText('aiR');

  // 2. Setup Configuration
  await page.fill('textarea[placeholder*="E.g., Examine"]', 'Explore the dataset');
  await page.click('button:has-text("Guided Mode")');
  
  // 3. Start Session
  await page.click('button:has-text("START SESSION")');

  // 4. Wait for Workspace
  await expect(page.getByTestId('chat-input')).toBeVisible({ timeout: 120000 });

  // 5. Verify Workspace Layout & State
  await expect(page.getByTestId('session-objective')).toContainText('Explore the dataset');

  // 6. Verify first coach response
  await expect(page.getByTestId('coach-what').first()).toBeVisible({ timeout: 120000 });
});
