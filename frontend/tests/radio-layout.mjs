// Uses a new isolated browser and refuses any API that can execute models.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.WORKBENCH_URL ?? 'http://127.0.0.1:5179';
const output = process.env.RADIO_LAYOUT_OUTPUT;
assert.ok(output, 'Set RADIO_LAYOUT_OUTPUT to an isolated screenshot directory');
const marker = await fetch(`${base}/api/__workbench_test__`).then(response => response.json());
assert.ok(marker.isolated && marker.model_execution === false, 'Refusing a non-isolated API');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH ?? '/opt/google/chrome/chrome', headless: true });
const measurements = [];
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  // Turn off finite presentation transitions, not wait for potentially endless animations.
  await page.addInitScript(() => localStorage.setItem('asr-studio:locale', 'ja'));
  async function visit(route, locale) {
    await page.goto(`${base}/${route}`);
    await page.locator('.page-heading').waitFor();
    await page.waitForLoadState('networkidle');
    await page.locator('.locale-control select').selectOption(locale);
    await page.waitForFunction(expected => document.documentElement.lang === expected, locale);
    await page.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; }' });
    await page.evaluate(async () => { await document.fonts.ready; scrollTo(0, 0); });
  }
  async function verifyGroup(group, expectedCount, name) {
    const buttons = group.locator('.n-radio-button');
    assert.equal(await buttons.count(), expectedCount, `${name}: all options present`);
    for (let index = 0; index < expectedCount; index++) {
      const button = buttons.nth(index);
      await button.scrollIntoViewIfNeeded();
      const measurement = await button.evaluate(element => {
        const rect = element.getBoundingClientRect();
        const group = element.closest('.n-radio-group');
        const groupRect = group.getBoundingClientRect();
        const clippedBy = [];
        for (let parent = element.parentElement; parent; parent = parent.parentElement) {
          const style = getComputedStyle(parent);
          const bounds = parent.getBoundingClientRect();
          const clipsX = /hidden|clip|scroll|auto/.test(style.overflowX);
          const clipsY = /hidden|clip|scroll|auto/.test(style.overflowY);
          if ((clipsX && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1)) || (clipsY && (rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1))) {
            clippedBy.push({ className: parent.className, top: bounds.top, bottom: bounds.bottom, overflowX: style.overflowX, overflowY: style.overflowY });
          }
        }
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        return {
          text: element.innerText, groupHeight: groupRect.height,
          insideGroup: rect.top >= groupRect.top - 1 && rect.bottom <= groupRect.bottom + 1,
          insideViewport: rect.left >= -1 && rect.right <= innerWidth + 1 && rect.top >= 0 && rect.bottom <= innerHeight,
          centerHit: !!hit && (element === hit || element.contains(hit)),
          hit: hit?.className, clippedBy,
        };
      });
      measurements.push({ name, ...measurement });
      assert.ok(measurement.insideGroup && measurement.insideViewport && measurement.centerHit && measurement.clippedBy.length === 0, `${name}: radio clipped or covered: ${JSON.stringify(measurement)}`);
      await button.click();
      assert.equal(await button.locator('input[type="radio"]').isChecked(), true, `${name}: option is operable`);
    }
  }
  // Japanese batch mode is the reported failure; keep this first to establish the red regression.
  for (const locale of ['ja', 'en', 'zh-CN']) {
    await visit('batch-job', locale);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, `batch-${locale}-before-check.png`), fullPage: true });
    await verifyGroup(page.locator('.mode-radio-group'), 4, `batch modes ${locale} 390px`);
    await page.locator('.mode-radio-group .n-radio-button').first().click();
    await verifyGroup(page.locator('.n-radio-group').nth(1), 2, `batch task types ${locale} 390px`);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, `batch-${locale}-390.png`), fullPage: true });
    for (const route of ['single-job', 'stage-runner', 'pdf-book-ocr']) {
      await visit(route, locale);
      await verifyGroup(page.locator('.n-radio-group').first(), 2, `${route} ${locale} 390px`);
    }
  }
  console.log('PASS: all four batch modes and all related radio groups are unclipped, hit-testable and selectable at 390px in ja/en/zh-CN');
} finally {
  await writeFile(path.join(output, 'radio-measurements.json'), JSON.stringify(measurements, null, 2));
  await browser.close();
}
