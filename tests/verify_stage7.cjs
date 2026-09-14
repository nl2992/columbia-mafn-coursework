/* Local browser acceptance. Requires the running viewer and Playwright/Chrome. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1092,height:1021},acceptDownloads:true});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:8765';
 const datasets=(await(await context.request.get(base+'/api/data')).json()).datasets;
 const csv=datasets.find(d=>d.path.endsWith('HO-5minHLV.csv')); assert.ok(csv);
 await page.goto(base+'/?view=data');
 await page.locator('#data-path option').filter({hasText:'HO-5minHLV.csv'}).waitFor({state:'attached'});
 await page.locator('#data-path').selectOption(csv.path);
 await page.locator('#data-status').filter({hasText:'Source verified.'}).waitFor();
 await page.locator('#data-range').fill('A1:G101');
 await page.locator('#data-operation').selectOption('mean');
 await page.locator('#data-column').fill('G');
 await page.locator('#data-date-format').selectOption('mdy');
 await page.locator('#data-run').click();
 await page.locator('#data-status').filter({hasText:'Complete.'}).waitFor({timeout:70000});
 assert.ok((await page.locator('#data-summary').textContent()).includes('100 matching rows'));
 assert.equal(await page.locator('#data-table tbody tr').count(),30);
 assert.ok((await page.locator('#data-schema').textContent()).includes('1984-01-03'));
 const downloaded=page.waitForEvent('download');await page.locator('#data-export').click();
 const file=await downloaded;const result=JSON.parse(fs.readFileSync(await file.path(),'utf8'));
 const lines=fs.readFileSync(csv.path,'utf8').trim().split(/\r?\n/).slice(1,101);
 const expected=lines.reduce((sum,line)=>sum+Number(line.split(',')[6]),0)/100;
 assert.ok(Math.abs(result.value-expected)<1e-10);assert.equal(result.recipe.range,'A1:G101');
 fs.mkdirSync('.rag/viewer/qa',{recursive:true});
 fs.writeFileSync('.rag/viewer/qa/stage7-result.json',JSON.stringify(result,null,2));
 for(const width of [1092,1440,768,390]) {
   await page.setViewportSize({width,height:1021});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Data overflow at '+width);
   await page.screenshot({path:`.rag/viewer/qa/data-${width}.png`,fullPage:true});
 }
 const saving=page.waitForResponse(response=>response.url().endsWith('/api/library/items') && response.request().method()==='POST' && response.request().postDataJSON().kind==='calculation');
 await page.locator('#data-save').click();
 const saved=await(await saving).json(); assert.ok(saved.id);
 await page.locator('#toast').filter({hasText:'Calculation saved'}).waitFor();
 await page.reload();await page.getByRole('button',{name:'Saved',exact:true}).click();
 await page.locator(`[data-saved-id="${saved.id}"]`).getByRole('button',{name:'Open',exact:true}).click();
 await page.locator('#data-status').filter({hasText:'source still matches'}).waitFor();
 assert.ok((await page.locator('#data-summary').textContent()).includes('SAVED SNAPSHOT'));
 const routeResponse=await context.request.post(base+'/api/ask',{data:{query:'Calculate average Volume in the CSV',filters:{course:['MATHGR5360']},source_paths:[csv.path]}});
 assert.equal(routeResponse.status(),200);const route=await routeResponse.json();
 assert.equal(route.route,'computation');assert.equal(route.claims.length,0);assert.equal(route.datasets.length,1);
 const rejected=await context.request.post(base+'/api/data/query',{data:{path:'../../etc/passwd',operation:'count'}});
 assert.equal(rejected.status(),400);
 const cross=await context.request.post(base+'/api/data/query',{headers:{Origin:'https://example.com'},data:{path:csv.path}});
 assert.equal(cross.status(),403);
 const removed=await context.request.post(base+'/api/library/delete',{data:{item_id:saved.id,revision:saved.revision}});assert.equal(removed.status(),200);
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({dataResultMatchesIndependentCalculation:true,range:result.range,mean:result.value,savedResultReopened:true,mobileOverflow:false,scopedRouter:true,sourceAndOriginGuards:true,temporarySavedItemRemoved:saved.id}));
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
