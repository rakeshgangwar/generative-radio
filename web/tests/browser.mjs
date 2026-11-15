// Opt-in local browser QA. Uses a temporary isolated profile, never a user profile.
import {chromium} from 'playwright-core';
import {checkBroadcast} from './broadcast-browser.mjs';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.RADIO_WEB_URL||'http://127.0.0.1:8080';
const artifacts=process.env.RADIO_WEB_ARTIFACTS||'../artifacts/listener-browser';
await mkdir(artifacts,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/opt/google/chrome/chrome',headless:true});
const results=[];
try {
  await checkBroadcast(browser,base,artifacts,results);
  const sleeping=await browser.newContext();
  const rest=await sleeping.newPage();
  const timerEpoch = Date.parse('2026-11-15T06:00:00Z');
  await rest.clock.setFixedTime(new Date(timerEpoch));
  async function timerTime(milliseconds) {
    await rest.clock.setFixedTime(new Date(timerEpoch + milliseconds));
    await rest.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  }
  await rest.goto(base);
  assert.equal(await rest.locator('#sleep-timer').count(),1,'sleep timer control must exist');
  await rest.getByLabel('Sleep timer',{exact:true}).selectOption('15');
  assert.equal(await rest.locator('#stream').getAttribute('src'),null,'arming must not autoplay');
  await rest.getByRole('button',{name:'Start listening',exact:true}).click();
  await rest.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing',null,{timeout:25000});
  await timerTime(890000);
  assert.ok(await rest.locator('#stream').evaluate(a=>a.volume>.28&&a.volume<.36),'last ten seconds attenuate volume');
  await rest.locator('#volume').evaluate(el=>{el.value=40;el.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.ok(await rest.locator('#stream').evaluate(a=>a.volume>.16&&a.volume<.24),'user volume retains fade gain');
  await timerTime(901000);
  assert.equal(await rest.locator('#player').getAttribute('data-state'),'paused');
  assert.equal(await rest.locator('#stream').getAttribute('src'),null);
  assert.equal(await rest.locator('#sleep-timer').inputValue(),'0');
  assert.match(await rest.locator('#timer-status').textContent(),/Timer ended/);
  await rest.getByRole('button',{name:'Resume listening',exact:true}).click();
  await rest.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  assert.ok(await rest.locator('#stream').evaluate(a=>Math.abs(a.volume-.4)<.001),'explicit resume restores chosen volume');
  await rest.getByLabel('Sleep timer',{exact:true}).selectOption('15');
  await timerTime(1791000);
  await rest.getByLabel('Sleep timer',{exact:true}).selectOption('0');
  assert.ok(await rest.locator('#stream').evaluate(a=>Math.abs(a.volume-.4)<.001),'Off restores chosen volume');
  await rest.getByRole('button',{name:'Pause',exact:true}).click();
  results.push({test:'real MP3 timer arming, fade/user volume, expiry/release and explicit resume',pass:true});
  await sleeping.close();

  const transient=await browser.newContext();const recoveringVolume=await transient.newPage();
  await recoveringVolume.clock.setFixedTime(new Date(timerEpoch));await recoveringVolume.goto(base);
  await recoveringVolume.getByRole('button',{name:'Start listening',exact:true}).click();
  await recoveringVolume.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  await recoveringVolume.getByLabel('Sleep timer',{exact:true}).selectOption('15');
  async function volumeTime(milliseconds) {
    await recoveringVolume.clock.setFixedTime(new Date(timerEpoch+milliseconds));
    await recoveringVolume.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  }
  await volumeTime(890000);
  assert.ok(await recoveringVolume.locator('#stream').evaluate(a=>Math.abs(a.volume-.325)<.001));
  await recoveringVolume.locator('#stream').evaluate(audio=>{
    const native=Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype,'volume');let failed=false;
    Object.defineProperty(audio,'volume',{configurable:true,get(){return native.get.call(this);},set(value){
      if(!failed&&value<.325){failed=true;throw new DOMException('Transient volume failure','NotSupportedError');}
      native.set.call(this,value);
    }});
  });
  await volumeTime(891000);await volumeTime(901000);
  assert.ok(await recoveringVolume.locator('#stream').evaluate(a=>Math.abs(a.volume-.65)<.001),'expiry restores after one transient mid-fade setter failure');
  assert.equal(await recoveringVolume.locator('#volume-control').isVisible(),true);
  await recoveringVolume.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  assert.match(await recoveringVolume.locator('#timer-status').textContent(),/Timer ended/);
  await recoveringVolume.getByRole('button',{name:'Resume listening',exact:true}).click();
  await recoveringVolume.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  assert.ok(await recoveringVolume.locator('#stream').evaluate(a=>Math.abs(a.volume-.65)<.001));
  results.push({test:'one mid-fade setter failure recovers chosen volume for manual playback',pass:true});await transient.close();

  const device=await browser.newContext({viewport:{width:390,height:844}});
  await device.addInitScript(() => Object.defineProperty(HTMLMediaElement.prototype, 'volume', {
    configurable:true, get(){return 1;}, set(){throw new DOMException('Device controls volume','NotSupportedError');}
  }));
  const devicePage=await device.newPage();await devicePage.clock.setFixedTime(new Date(timerEpoch));
  await devicePage.goto(base);
  assert.equal(await devicePage.locator('#volume-control').isVisible(),false);
  assert.equal(await devicePage.locator('#volume-note').isVisible(),true);
  await devicePage.getByRole('button',{name:'Start listening',exact:true}).click();
  await devicePage.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing');
  await devicePage.getByLabel('Sleep timer',{exact:true}).selectOption('15');
  await devicePage.screenshot({path:`${artifacts}/device-timer.png`,fullPage:true});
  await devicePage.clock.setFixedTime(new Date(timerEpoch+901000));
  await devicePage.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  assert.equal(await devicePage.locator('#player').getAttribute('data-state'),'paused');
  assert.equal(await devicePage.locator('#stream').getAttribute('src'),null);
  results.push({test:'device-owned volume still expires and releases real audio',pass:true});await device.close();

  const timerRecovery=await browser.newContext();let timerRequests=0;
  await timerRecovery.route('**/radio.mp3?*',route=>{timerRequests++;return route.abort('failed');});
  const stopped=await timerRecovery.newPage();await stopped.clock.setFixedTime(new Date(timerEpoch));
  await stopped.goto(base);await stopped.getByRole('button',{name:'Start listening',exact:true}).click();
  await stopped.waitForFunction(()=>document.querySelector('#player').dataset.state==='retrying');
  await stopped.getByLabel('Sleep timer',{exact:true}).selectOption('15');
  await stopped.clock.setFixedTime(new Date(timerEpoch+901000));
  await stopped.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  const requestsAtExpiry=timerRequests;
  await stopped.waitForTimeout(1200);
  assert.equal(await stopped.locator('#player').getAttribute('data-state'),'paused');
  assert.equal(await stopped.locator('#stream').getAttribute('src'),null);
  assert.equal(timerRequests,requestsAtExpiry,'expired timer must cancel queued reconnection');
  results.push({test:'timer expiry cancels real failed-request retry',pass:true});await timerRecovery.close();

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
