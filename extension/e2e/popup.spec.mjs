import { test, expect } from '@playwright/test';
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const extensionPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');

test.describe('PrivacyLens browser flow', () => {
  let context;
  let popup;

  test.beforeEach(async () => {
    context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
        '--no-sandbox'
      ]
    });
    let serviceWorker = context.serviceWorkers()[0];
    if (!serviceWorker) {
      serviceWorker = await context.waitForEvent('serviceworker', { timeout: 45_000 });
    }
    const extensionId = new URL(serviceWorker.url()).hostname;
    popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/src/popup/index.html`);
  });

  test.afterEach(async () => {
    if (context) await context.close();
  });

  test('keeps monitoring and policy fetching off until independently enabled', async () => {
    await expect(popup.getByRole('button', { name: 'Enable local monitoring' })).toBeVisible();
    await expect(popup.getByRole('button', { name: 'Policy Off' })).toBeVisible();
    await popup.getByRole('button', { name: 'Policy Off' }).click();
    await expect(popup.getByRole('button', { name: 'Policy On' })).toBeVisible();
    await popup.getByRole('button', { name: 'Enable local monitoring' }).click();
    await expect(popup.getByRole('button', { name: 'Pause' })).toBeVisible();
    await popup.getByRole('button', { name: 'Policy On' }).click();
    await expect(popup.getByRole('button', { name: 'Policy Off' })).toBeVisible();
  });

  test('shows local evidence when the API is unavailable', async () => {
    await popup.getByRole('button', { name: 'Enable local monitoring' }).click();
    await expect(popup.getByRole('button', { name: 'Pause' })).toBeVisible({
      timeout: 10_000
    });
  });
});
