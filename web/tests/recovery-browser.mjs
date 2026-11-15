// Faults are scoped to this temporary browser context; the station stays live.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
export async function checkLongRecovery(browser,base,artifacts,results) {
  const context=await browser.newContext({viewport:{width:390,height:844}});
  const page=await context.newPage(),requests=[],errors=[];
  let began,pass=false,diagnostic;
  page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/radio.mp3?*',route=>{
    const elapsed=Date.now()-began,failed=elapsed<30000;
    requests.push({elapsed,failed});return failed?route.abort('failed'):route.continue();
  });
  try {
    await page.goto(base);await page.getByLabel('Sleep timer',{exact:true}).selectOption('15');
    began=Date.now();
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForTimeout(15000);
    const early=await page.locator('#player').getAttribute('data-state');
    assert.notEqual(early,'error','thirty-second outage must not exhaust recovery at fifteen seconds');
    await page.waitForFunction(()=>document.querySelector('#player').dataset.state==='playing',null,{timeout:55000});
    await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1);
    assert.equal(await page.locator('#sleep-timer').inputValue(),'15');
    assert.match(await page.locator('#timer-remaining').textContent(),/Stops in 14:/);
    assert.ok(requests.some(r=>r.failed&&r.elapsed>=12000));
    assert.ok(requests.some(r=>!r.failed&&r.elapsed>=30000));
    const title=await page.locator('#broadcast-context-title').textContent();
    await page.screenshot({path:`${artifacts}/recovered-after-30s.png`,fullPage:true});
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    const count=requests.length;await page.waitForTimeout(1200);assert.equal(requests.length,count);
    assert.deepEqual(errors,[]);pass=true;
    results.push({test:'thirty-second failed media requests recover with one gesture, real audio advances, sleep timer survives and pause cancels recovery',pass:true});
  } catch(error) {diagnostic=String(error);throw error;}
  finally {
    let state;
    try {state=await page.locator('#player').getAttribute('data-state');}catch{}
    await writeFile(`${artifacts}/recovery-long-outage.json`,JSON.stringify({pass,requests,errors,state,diagnostic,scope:'Thirty-second failed requests in one Chromium context; live station unmodified.'},null,2)+'\n');
    await context.close();
  }
}
