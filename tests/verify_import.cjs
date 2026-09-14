const {chromium} = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const page = await browser.newPage({viewport:{width:1092, height:900}});
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const base = process.env.RAG_TEST_URL || 'http://127.0.0.1:8765';
  try {
    await page.goto(base + '/?view=import');
    await page.locator('#index-status').filter({hasText:'Library ready'}).waitFor();
    await page.waitForFunction(() => document.querySelectorAll('#import-folder option').length > 1);
    assert.match(await page.locator('#page-title').textContent(), /Add documents/);
    assert.match(await page.locator('#import-publish-target').textContent(), /main.*github\.com[:/]nl2992\/columbia-mafn-coursework/);
    const folder = await page.locator('#import-folder option').evaluateAll(options => options.find(option => /MATHGR5010.*lectures/.test(option.textContent)).value);
    await page.locator('#import-folder').selectOption(folder);
    await page.locator('#import-files').setInputFiles({name:'browser-acceptance.txt', mimeType:'text/plain', buffer:Buffer.from('Browser selection acceptance only.')});
    assert.equal(await page.locator('#import-submit').isEnabled(), true);
    assert.match(await page.locator('#import-file-list').textContent(), /browser-acceptance\.txt/);
    assert.match(await page.locator('#import-validation').textContent(), /ready for local verification/);
    for (const width of [390, 768, 1092, 1440]) {
      await page.setViewportSize({width, height:900});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    assert.deepEqual(errors, []);
    console.log('PASS: intake route, folder target, file validation, GitHub target, and four viewport widths');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
