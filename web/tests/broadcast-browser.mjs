// Actual Chromium/media integration; request faults stay confined to this context.
import assert from 'node:assert/strict';
export async function checkBroadcast(browser,base,artifacts,results) {
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(()=>{
    window.contextRequests=[];
    const native=window.fetch.bind(window);
    window.fetch=(url,options)=>{
      if(url==='/broadcast.json') {
        const record={at:performance.now(),aborted:false};window.contextRequests.push(record);
        options.signal.addEventListener('abort',()=>{record.aborted=true;},{once:true});
      }
      return native(url,options);
    };
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let mode='real',held;
  await context.route('**/broadcast.json',async route=>{
    if(mode==='real') return route.continue();
    if(mode==='malicious') return route.fulfill({contentType:'application/json',body:JSON.stringify({version:1,available:true,title:'<img src=x onerror="window.contextXss=true">'})});
    if(mode==='failed') return route.fulfill({status:503,body:'unavailable'});
    await new Promise(resolve=>{held=resolve;});await route.abort().catch(()=>{});
  });
  try {
    await page.goto(base);
    assert.equal(await page.locator('#broadcast-context').isVisible(),false);
    assert.equal(await page.evaluate(()=>contextRequests.length),0,'idle must not fetch metadata');
    const response=await context.request.get(base+'/broadcast.json');
    assert.equal(response.status(),200);assert.match(response.headers()['content-type'],/application\/json/);
    assert.match(response.headers()['cache-control'],/no-store/);
    const payload=await response.json();assert.deepEqual(Object.keys(payload).sort(),['available','title','version']);
    assert.equal(payload.version,1);assert.equal(payload.available,true);
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
    await page.waitForFunction(()=>!document.querySelector('#broadcast-context').hidden);
    assert.match(await page.locator('#broadcast-context-title').textContent(),/^(Chapter \d+ is |A quiet interlude\.|Original ambient music\.)/);
    await page.getByLabel('Sleep timer',{exact:true}).selectOption('15');
    const started=await page.locator('#stream').evaluate(a=>a.currentTime);
    await page.screenshot({path:`${artifacts}/context-desktop.png`,fullPage:true});
    for(const width of [390,320]) {
      await page.setViewportSize({width,height:width===390?844:640});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:`${artifacts}/context-${width}.png`,fullPage:true});
    }
    mode='malicious';
    await page.waitForFunction(()=>document.querySelector('#broadcast-context-title').textContent.startsWith('<img'),null,{timeout:15000});
    assert.equal(await page.locator('#broadcast-context-title img').count(),0);
    assert.equal(await page.evaluate(()=>window.contextXss),undefined);
    assert.equal(await page.locator('#sleep-timer').inputValue(),'15');
    mode='failed';
    await page.waitForFunction(()=>document.querySelector('#broadcast-context').hidden,null,{timeout:15000});
    assert.equal(await page.locator('#player').getAttribute('data-state'),'playing');
    assert.ok(await page.locator('#stream').evaluate(a=>a.currentTime)>started+5);
    mode='held';
    const before=await page.evaluate(()=>contextRequests.length);
    await page.waitForFunction(n=>contextRequests.length>n,before,{timeout:15000});
    await page.evaluate(()=>{
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
      document.dispatchEvent(new Event('visibilitychange'));
    });
    assert.equal(await page.evaluate(()=>contextRequests.at(-1).aborted),true,'hidden aborts owned request');
    const hiddenCount=await page.evaluate(()=>contextRequests.length);
    await page.waitForTimeout(10500);
    assert.equal(await page.evaluate(()=>contextRequests.length),hiddenCount,'hidden does not poll');
    assert.equal(await page.locator('#player').getAttribute('data-state'),'playing');
    held?.();held=undefined;
    await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});
    await page.waitForFunction(n=>contextRequests.length>n,hiddenCount);
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    assert.equal(await page.evaluate(()=>contextRequests.at(-1).aborted),true,'pause aborts owned request');
    held?.();held=undefined;
    assert.equal(await page.locator('#broadcast-context').isVisible(),false);
    const pausedCount=await page.evaluate(()=>contextRequests.length);
    await page.waitForTimeout(10500);
    assert.equal(await page.evaluate(()=>contextRequests.length),pausedCount,'paused does not poll');
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    assert.deepEqual(errors,[]);
    results.push({test:'real public context, idle/pause/hidden lifecycle, XSS-as-text, failed metadata independent of real audio and sleep timer, 320/390/desktop layouts',pass:true});
  } finally {held?.();await context.close();}
}
