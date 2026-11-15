import assert from 'node:assert/strict';

const preferenceKey='generative-radio.volume.v1';
async function chooseVolume(page,value) {
  await page.locator('#volume').focus();await page.keyboard.press('Home');
  for(let i=0;i<value;i++) await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#volume').inputValue(),String(value));
}

export async function checkVolumeMemory(browser,base,artifacts,results) {
  const context=await browser.newContext({viewport:{width:320,height:640}});
  try {
    const page=await context.newPage(),requests=[];
    page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests.push(request.url());});
    await page.goto(base);
    assert.equal(await page.locator('#volume').inputValue(),'65');
    assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),null,'page load must not create a preference');
    await chooseVolume(page,37);
    await page.getByLabel('Sleep timer',{exact:true}).selectOption('15');
    assert.equal(requests.length,0,'volume/timer input must not autoplay');
    await page.reload();
    assert.equal(await page.locator('#volume').inputValue(),'37','chosen quiet volume must survive page refresh');
    assert.equal(await page.locator('#volume-value').textContent(),'37%');
    assert.equal(await page.locator('#volume').getAttribute('aria-valuetext'),'37 percent');
    assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.37)<.001));
    assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),'37');
    assert.equal(await page.locator('#sleep-timer').inputValue(),'0','timer remains page-local');
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    assert.equal(requests.length,0,'refresh must keep manual playback intent');
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
    assert.equal(requests.length,1);
    await page.screenshot({path:`${artifacts}/restored-volume-320.png`,fullPage:true});
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    assert.equal(await page.locator('#stream').getAttribute('src'),null);
    results.push({test:'chosen quiet volume survives refresh with matching audio/ARIA, no autoplay and reset timer',pass:true});
  } finally {await context.close();}

  for(const value of [0,100]) {
    const context=await browser.newContext();
    try {
      const page=await context.newPage();let requests=0;
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests++;});
      await page.goto(base);await page.locator('#volume').focus();await page.keyboard.press(value===0?'Home':'End');
      await page.reload();
      assert.equal(await page.locator('#volume').inputValue(),String(value));
      assert.equal(await page.locator('#volume-value').textContent(),`${value}%`);
      assert.equal(await page.locator('#volume').getAttribute('aria-valuetext'),`${value} percent`);
      assert.ok(await page.locator('#stream').evaluate((audio,value)=>Math.abs(audio.volume-value/100)<.001,value));
      assert.equal(requests,0);
      results.push({test:`saved volume boundary ${value} restores audio/readout without autoplay`,pass:true});
    } finally {await context.close();}
  }

  const invalid=['',' 37','37\n','037','-0','-1','101','99.5','1e2','NaN','{"volume":37}','9'.repeat(4096)];
  for(const value of invalid) {
    const context=await browser.newContext();
    try {
      await context.addInitScript(({key,value})=>localStorage.setItem(key,value),{key:preferenceKey,value});
      const page=await context.newPage(),errors=[];let requests=0;
      page.on('pageerror',error=>errors.push(error.message));
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests++;});
      await page.goto(base);
      assert.equal(await page.locator('#enhanced-controls').isVisible(),true);
      assert.equal(await page.locator('#volume').inputValue(),'65');
      assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.65)<.001));
      assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),value,'initialization must not rewrite stored data');
      assert.equal(requests,0);assert.deepEqual(errors,[]);
    } finally {await context.close();}
  }
  results.push({test:'twelve invalid/oversized/noncanonical preferences keep default without writes, errors or autoplay',pass:true});

  for(const failure of ['getter','write']) {
    const context=await browser.newContext();
    try {
      await context.addInitScript(({key,failure})=>{
        if(failure==='getter') Object.defineProperty(window,'localStorage',{configurable:true,get(){throw new DOMException('fixture storage denied','SecurityError');}});
        else {
          localStorage.setItem(key,'37');
          const native=Storage.prototype.setItem;
          Storage.prototype.setItem=function(name,value){if(name===key)throw new DOMException('fixture storage full','QuotaExceededError');return native.call(this,name,value);};
        }
      },{key:preferenceKey,failure});
      const page=await context.newPage(),errors=[];let requests=0;
      page.on('pageerror',error=>errors.push(error.message));
      page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests++;});
      await page.goto(base);
      assert.equal(await page.locator('#volume').inputValue(),failure==='getter'?'65':'37');
      await chooseVolume(page,40);
      assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.4)<.001));
      assert.equal(await page.locator('#volume-value').textContent(),'40%');
      assert.equal(requests,0);assert.deepEqual(errors,[]);
      if(failure==='write') assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),'37');
      else {
        await page.getByRole('button',{name:'Start listening',exact:true}).click();
        await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
        assert.equal(requests,1);
      }
      results.push({test:`simulated storage ${failure} failure preserves volume controls and manual listening`,pass:true});
    } finally {await context.close();}
  }

  const fading=await browser.newContext();
  try {
    const page=await fading.newPage(),epoch=Date.parse('2026-11-15T14:00:00Z');let requests=0;
    page.on('request',request=>{if(new URL(request.url()).pathname==='/radio.mp3')requests++;});
    await page.clock.setFixedTime(new Date(epoch));await page.goto(base);await chooseVolume(page,37);
    await page.getByRole('button',{name:'Start listening',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
    await page.getByLabel('Sleep timer',{exact:true}).selectOption('15');
    await page.clock.setFixedTime(new Date(epoch+890000));await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
    assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.185)<.01));
    assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),'37','fade must not replace requested preference');
    await chooseVolume(page,40);
    assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.2)<.01),'new user input retains current fade gain');
    assert.equal(await page.evaluate(key=>localStorage.getItem(key),preferenceKey),'40','save requested level rather than attenuated audio volume');
    await page.reload();
    assert.equal(await page.locator('#volume').inputValue(),'40');
    assert.ok(await page.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.4)<.001));
    assert.equal(await page.locator('#sleep-timer').inputValue(),'0');
    assert.equal(await page.locator('#stream').getAttribute('src'),null);assert.equal(requests,1);
    results.push({test:'reload during a real playing fade restores requested volume, not gain, without playback or timer persistence',pass:true});
  } finally {await fading.close();}

  const shared=await browser.newContext();
  try {
    const first=await shared.newPage();await first.goto(base);await chooseVolume(first,30);
    await first.getByRole('button',{name:'Start listening',exact:true}).click();
    await first.waitForFunction(()=>document.querySelector('#stream').currentTime>1,null,{timeout:25000});
    const second=await shared.newPage();await second.goto(base);assert.equal(await second.locator('#volume').inputValue(),'30');
    await chooseVolume(second,70);await first.bringToFront();
    assert.equal(await first.locator('#volume').inputValue(),'30');
    assert.ok(await first.locator('#stream').evaluate(audio=>Math.abs(audio.volume-.3)<.001));
    assert.equal(await first.locator('#player').getAttribute('data-state'),'playing');
    assert.equal(await first.evaluate(key=>localStorage.getItem(key),preferenceKey),'70');
    await first.reload();assert.equal(await first.locator('#volume').inputValue(),'70');
    assert.equal(await first.locator('#stream').getAttribute('src'),null);
    results.push({test:'another tab changes future preference without jumping ongoing audio; refresh applies it without autoplay',pass:true});
  } finally {await shared.close();}
}
