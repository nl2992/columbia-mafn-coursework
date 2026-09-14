const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const context = await browser.newContext({viewport:{width:1092,height:900}});
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const base = process.env.RAG_TEST_URL || 'http://127.0.0.1:8765';
  let item;
  try {
    await page.goto(base);
    await page.locator('#index-status').filter({hasText:'Library ready'}).waitFor();
    await page.locator('#filter-panel summary').click();
    await page.locator('#query').fill('gamma');
    await page.locator('#file-filter').selectOption('pdf');
    await page.locator('#view-title').fill('Stage 8 acceptance view');
    await page.locator('#save-view').click();
    await page.locator('#toast').filter({hasText:'Filter view saved'}).waitFor();
    const items = (await (await context.request.get(base+'/api/library')).json()).items;
    item = items.find(i => i.title === 'Stage 8 acceptance view'); assert.ok(item);
    await page.reload();
    await page.locator('[data-view="saved"]').click();
    await page.locator(`[data-saved-id="${item.id}"] [data-action="open"]`).click();
    await page.waitForFunction(() => document.getElementById('query').value === 'gamma');
    assert.equal(await page.locator('#query').inputValue(),'gamma');
    assert.equal(await page.locator('#file-filter').inputValue(),'pdf');
    await page.locator('[data-view="coverage"]').click();
    await page.locator('#refresh-jobs').click();
    await page.locator('#operations-status').filter({hasText:'complete'}).waitFor();
    for (const width of [390,768,1092,1440]) {
      await page.setViewportSize({width,height:900});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    assert.deepEqual(errors,[]);
    console.log('PASS: saved filters survive reload, reopen exact scope, refresh history, four viewport widths');
  } finally {
    if (item) await context.request.post(base+'/api/library/delete',{data:{item_id:item.id,revision:item.revision}});
    await browser.close();
  }
})().catch(error => {console.error(error);process.exit(1);});
