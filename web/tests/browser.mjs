// Opt-in local browser QA. Uses a temporary isolated profile, never a user profile.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.RADIO_WEB_URL||'http://127.0.0.1:8080';
const artifacts=process.env.RADIO_WEB_ARTIFACTS||'../artifacts/listener-browser';
await mkdir(artifacts,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/opt/google/chrome/chrome',headless:true});
const results=[];
try {
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const page=await context.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(base,{waitUntil:'load'});
  assert.equal(await page.locator('#player').getAttribute('data-state'),'idle');
  assert.equal(requests.some(url=>url.includes('/radio.mp3')),false);
  await page.getByRole('button',{name:'Start listening',exact:true}).focus();await page.keyboard.press('Space');
  await page.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing',null,{timeout:25000});
  await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1);
  const volume=page.locator('#volume');await volume.focus();await page.keyboard.press('Home');await page.keyboard.press('ArrowRight');
  assert.ok(await page.locator('#stream').evaluate(a=>Math.abs(a.volume-.01)<.001));
  await volume.evaluate(el=>{el.value=65;el.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.screenshot({path:`${artifacts}/desktop.png`,fullPage:true});
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  assert.equal(await page.locator('#player').getAttribute('data-state'),'paused');assert.equal(await page.locator('#stream').getAttribute('src'),null);
  await page.getByRole('button',{name:'Resume listening',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  await page.getByRole('button',{name:'Pause',exact:true}).click();assert.deepEqual(errors,[]);
  results.push({test:'real stream, keyboard, volume, pause/release and live resume',pass:true});await context.close();

  const mobile=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  const phone=await mobile.newPage();await phone.goto(base);
  assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await phone.getByRole('button',{name:'Start listening',exact:true}).click();
  await phone.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  assert.equal(await phone.locator('.dial img').evaluate(e=>getComputedStyle(e).animationName),'none');
  await phone.getByRole('button',{name:'Pause',exact:true}).click();
  const rect=await phone.locator('#toggle').boundingBox();assert.ok(rect.y+rect.height<844);
  await phone.screenshot({path:`${artifacts}/mobile.png`,fullPage:true});
  await phone.setViewportSize({width:320,height:640});assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await phone.screenshot({path:`${artifacts}/narrow.png`,fullPage:true});
  results.push({test:'390px/320px layout, visible play and reduced motion',pass:true});await mobile.close();

  const recovery=await browser.newContext();let streams=0;
  await recovery.route('**/radio.mp3?*',route=>++streams===1?route.abort('failed'):route.continue());
  const recovering=await recovery.newPage();await recovering.goto(base);
  await recovering.getByRole('button',{name:'Start listening',exact:true}).click();
  await recovering.waitForFunction(()=>document.querySelector('#player').dataset.state==='retrying',null,{timeout:10000});
  await recovering.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing',null,{timeout:25000});assert.equal(streams,2);
  await recovering.getByRole('button',{name:'Pause',exact:true}).click();
  results.push({test:'real failed media request automatically reconnects',pass:true});await recovery.close();

  const pending=await browser.newContext();let pendingRequests=0;
  await pending.route('**/radio.mp3?*',async route=>{
    pendingRequests++;await new Promise(resolve=>setTimeout(resolve,1200));
    await route.continue().catch(()=>{});
  });
  const cancelling=await pending.newPage();await cancelling.goto(base);
  const requested=cancelling.waitForRequest(request=>new URL(request.url()).pathname==='/radio.mp3');
  await cancelling.getByRole('button',{name:'Start listening',exact:true}).click();
  await requested;await cancelling.waitForFunction(()=>!document.querySelector('#stream').paused);
  await cancelling.locator('#stream').evaluate(audio=>audio.pause());
  await cancelling.waitForFunction(()=>document.querySelector('#player').dataset.state==='paused',null,{timeout:2000});
  await cancelling.waitForTimeout(1600);
  assert.equal(pendingRequests,1);assert.equal(await cancelling.locator('#stream').evaluate(audio=>audio.paused),true);
  assert.equal(await cancelling.locator('#player').getAttribute('data-state'),'paused');
  results.push({test:'native pause during pending connection cancels automatic retries',pass:true});await pending.close();

  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:640}});const native=await nojs.newPage();await native.goto(base);
  assert.equal(await native.locator('audio[controls]').count(),1);
  assert.equal(await native.locator('#enhanced-controls').isVisible(),false);
  assert.equal(await native.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  results.push({test:'native no-JavaScript audio fallback',pass:true});await nojs.close();
  await writeFile(`${artifacts}/result.json`,JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results,null,2));
} finally {await browser.close();}
