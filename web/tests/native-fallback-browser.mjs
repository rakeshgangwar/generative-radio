import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
// Exact HTML shipped before native fallback (main5ab28f9), with candidate scripts.
const legacyHTML=readFileSync(new URL('./fixtures/listener-before-native.html',import.meta.url),'utf8');

// Use native controls through a trusted keyboard action, not an injected play().
async function startNative(page) {
  const audio=page.locator('#native-stream');
  await audio.focus();
  await page.keyboard.press('Space');
  // Page-side requestAnimationFrame polling is disabled in a JS-off context.
  // Read the native clock from the driver instead; do not enable page scripts.
  const deadline=Date.now()+25000;
  let media;
  do {
    media=await audio.evaluate(a=>({time:a.currentTime,paused:a.paused,ready:a.readyState,error:a.error?.code??null}));
    if(media.time>1) return;
    await new Promise(resolve=>setTimeout(resolve,100));
  } while(Date.now()<deadline);
  assert.fail(`native keyboard playback did not advance: ${JSON.stringify(media)}`);
}

export async function checkNativeFocus(browser,base,artifacts,results) {
  for(const focused of ['#native-stream','.wordmark']) {
    const context=await browser.newContext({viewport:{width:320,height:640}});
    let release;
    const gate=new Promise(resolve=>release=resolve);
    try {
      const page=await context.newPage(),requests=[];
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
      await page.route('**/app.js',async route=>{
        const response=await route.fetch(),body=await response.text();
        await gate;
        await route.fulfill({response,body:body+'\nwindow.__nativeScriptEvaluated=true;'});
      });
      await page.goto(base,{waitUntil:'commit'});
      await page.locator('#native-stream').waitFor({state:'visible'});
      await page.locator(focused).focus();
      assert.equal(await page.locator(focused).evaluate(element=>element===document.activeElement),true);
      release();
      await page.waitForFunction(()=>window.__nativeScriptEvaluated===true);
      assert.equal(await page.locator('#enhanced-controls').isVisible(),true);
      assert.equal(await page.locator('#native-fallback').isVisible(),false);
      const expected=focused==='#native-stream'?'#toggle':focused;
      assert.equal(await page.locator(expected).evaluate(element=>element===document.activeElement),true,'late enhancement must keep keyboard focus on a visible intended control');
      assert.equal(await page.locator('#native-stream').getAttribute('src'),null);
      assert.equal(requests.length,0,'focus transfer must not autoplay');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      if(focused==='#native-stream') {
        await page.screenshot({path:`${artifacts}/enhanced-focus-320.png`,fullPage:true});
        await page.keyboard.press('Space');
        await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
        assert.equal(requests.length,1,'keyboard play after handoff opens one real stream');
        await page.keyboard.press('Space');
        assert.equal(await page.locator('#stream').getAttribute('src'),null);
      }
      results.push({test:focused==='#native-stream'?'late enhancement transfers native focus to visible play; Space starts/releases real audio':'late enhancement preserves unrelated link focus without autoplay',pass:true});
    } finally {release();await context.close();}
  }
}

export async function checkNativeFallback(browser,base,artifacts,results) {
  await checkNativeFocus(browser,base,artifacts,results);
  const legacy=await browser.newContext();
  try {
    const page=await legacy.newPage(),errors=[],requests=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
    await page.route(new URL('/',base).href,route=>route.fulfill({status:200,contentType:'text/html',body:legacyHTML}));
    await page.goto(base);
    assert.equal(await page.locator('#native-stream').count(),0,'fixture must use actual predeployment HTML');
    assert.equal(await page.locator('#enhanced-controls').isVisible(),true,'previous HTML with new app must retain a usable player');
    assert.deepEqual(errors,[]);
    assert.equal(requests.length,0);
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
    assert.equal(requests.length,1);
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    results.push({test:'previous deployed HTML with candidate scripts starts and releases real MP3',pass:true});
  } finally {await legacy.close();}

  for(const failed of ['app.js','sleep-timer.js','javascript-off','initialization']) {
    const context=await browser.newContext({viewport:{width:320,height:640},javaScriptEnabled:failed!=='javascript-off'});
    try {
      const page=await context.newPage(),requests=[];
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
      const errors=[];page.on('pageerror',error=>errors.push(error.message));
      if(failed==='initialization') {
        await page.addInitScript(()=>Object.defineProperty(navigator,'mediaSession',{configurable:true,get(){throw new Error('native-fallback initialization fixture');}}));
      } else if(failed!=='javascript-off') {
        await page.route(`**/${failed}`,route=>route.abort('failed'));
      }
      await page.goto(base);
      assert.equal(await page.locator('#native-fallback').isVisible(),true,`${failed} failure must leave native controls`);
      assert.equal(await page.locator('#enhanced-controls').isVisible(),false);
      if(failed==='initialization') assert.ok(errors.some(error=>error.includes('native-fallback initialization fixture')),'initialization fault must actually execute');
      assert.equal(requests.length,0,'native preload=none must not request music before play');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await startNative(page);
      assert.equal(requests.length,1,'native listening opens one stream');
      await page.screenshot({path:`${artifacts}/native-${failed}.png`,fullPage:true});
      results.push({test:`native keyboard playback after ${failed} failure at320px`,pass:true});
    } finally {await context.close();}
  }

  for(const phase of ['playing','paused','pending']) {
    const context=await browser.newContext();
    let releaseModule,releaseAudio,signalAudioHeld;
    const moduleGate=new Promise(resolve=>releaseModule=resolve);
    const audioGate=new Promise(resolve=>releaseAudio=resolve);
    const audioHeld=new Promise(resolve=>signalAudioHeld=resolve);
    try {
      const page=await context.newPage(),requests=[];
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
      await page.route('**/app.js',async route=>{
        const response=await route.fetch(),body=await response.text();
        await moduleGate;
        await route.fulfill({response,body:body+'\nwindow.__nativeScriptEvaluated=true;'});
      });
      await page.addInitScript(()=>{const storage=window.localStorage;window.__volumeStorageAccesses=0;Object.defineProperty(window,'localStorage',{configurable:true,get(){window.__volumeStorageAccesses++;return storage;}});});
      if(phase==='pending') await page.route('**/radio.mp3',async route=>{signalAudioHeld();await audioGate;await route.continue();});
      await page.goto(base,{waitUntil:'commit'});
      await page.locator('#native-stream').waitFor({state:'visible'});
      assert.equal(requests.length,0,'delayed enhancement still must not autoplay');
      if(phase==='pending') {
        await page.locator('#native-stream').focus();await page.keyboard.press('Space');
        await audioHeld;
        assert.equal(await page.locator('#native-stream').evaluate(audio=>audio.paused),false);
        assert.equal(requests.length,1);
      } else {
        await startNative(page);
        if(phase==='paused') {
          await page.keyboard.press('Space');
          await page.waitForFunction(()=>document.querySelector('#native-stream').paused);
          assert.ok(await page.locator('#native-stream').evaluate(audio=>audio.played.length>0));
        }
      }
      const source=await page.locator('#native-stream').getAttribute('src');
      const before=await page.locator('#native-stream').evaluate(audio=>audio.currentTime);
      releaseModule();
      await page.waitForFunction(()=>window.__nativeScriptEvaluated===true);
      assert.equal(await page.locator('#native-fallback').isVisible(),true);
      assert.equal(await page.evaluate(()=>window.__volumeStorageAccesses),0,'started native session must return before preference access');
      assert.equal(await page.locator('#native-stream').evaluate(audio=>audio===document.activeElement),true,'started native session retains keyboard focus');
      assert.equal(await page.locator('#enhanced-controls').isVisible(),false);
      assert.equal(await page.locator('#native-stream').getAttribute('src'),source);
      assert.equal(await page.locator('#stream').getAttribute('src'),null);
      assert.equal(requests.length,1,'late enhancement must not open another connection');
      if(phase==='paused') {
        assert.equal(await page.locator('#native-stream').evaluate(audio=>audio.paused),true);
        await page.keyboard.press('Space');
      }
      releaseAudio();
      await page.waitForFunction(before=>document.querySelector('#native-stream').currentTime>before+.5,before,{timeout:25000});
      assert.equal(requests.length,1,'preserved native session continues on its existing source');
      results.push({test:`late module preserves ${phase} native session and one connection`,pass:true});
    } finally {releaseModule();releaseAudio();await context.close();}
  }

  const context=await browser.newContext();
  try {
    const page=await context.newPage(),requests=[];
    page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
    await page.goto(base);
    assert.equal(await page.locator('#enhanced-controls').isVisible(),true);
    assert.equal(await page.locator('#native-fallback').isVisible(),false);
    assert.equal(await page.locator('#native-stream').getAttribute('src'),null);
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    assert.equal(requests.length,0);
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
    assert.equal(requests.length,1);
    results.push({test:'normal enhancement releases unused native source and opens one stream on click',pass:true});
  } finally {await context.close();}
}
