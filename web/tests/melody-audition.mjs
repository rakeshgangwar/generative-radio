// Browser acceptance for a completed offline melody pair; no station controls.
import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.RADIO_MELODY_URL||'http://127.0.0.1:18091';
const out=process.env.RADIO_MELODY_ARTIFACTS||'artifacts/melody-audition-browser';await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/opt/google/chrome/chrome',headless:true});const errors=[],requests=[];let pass=false,diagnostic;
try {
 const page=await browser.newPage({viewport:{width:1280,height:1000}});page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
 const response=await page.goto(base);assert.equal(response.status(),200);assert.match(await page.title(),/Melody audition/);
 assert.equal(await page.locator('audio').count(),2);assert.equal(requests.some(u=>u.endsWith('.mp3')),false);
 const data=await (await page.request.get(base+'/report.json')).json();assert.equal(data.status,'complete');assert.ok(data.added_notes>0,'use positions with audible score changes');assert.ok(data.sequence_seconds>=20);
 const audio=page.locator('audio');const cue=data.changes[0].sequence_seconds;
 const seconds=Math.floor(cue),name=`Compare near ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
 const guide=page.getByRole('button',{name,exact:true});assert.equal(await guide.count(),1,'time guides must be actionable');assert.ok((await guide.boundingBox()).height>=44,'touch target must be usable');
 await guide.click();const seek=Math.max(0,cue-3);
 await page.waitForFunction(t=>[...document.querySelectorAll('audio')].every(a=>a.paused&&Math.abs(a.currentTime-t)<.2),seek);
 await audio.nth(0).click({position:{x:25,y:27}});
 await page.waitForFunction(t=>document.querySelectorAll('audio')[0].currentTime>t+.5,seek);
 await audio.nth(1).click({position:{x:25,y:27}});
 await page.waitForFunction(t=>document.querySelectorAll('audio')[1].currentTime>t+.5,seek);
 assert.equal(await audio.nth(0).evaluate(a=>a.paused),true,'starting B pauses A');
 await guide.click();await page.waitForFunction(t=>[...document.querySelectorAll('audio')].every(a=>a.paused&&Math.abs(a.currentTime-t)<.2),seek);
 await page.screenshot({path:out+'/desktop.png',fullPage:true});
 for(const width of [390,320]){await page.setViewportSize({width,height:width===390?844:640});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:out+`/${width}.png`,fullPage:true});}
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:640}});const fallback=await nojs.newPage();await fallback.goto(base);assert.equal(await fallback.locator('audio[controls]').count(),2);assert.equal(await fallback.locator('[data-seek]:enabled').count(),0);assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await nojs.close();
 await audio.nth(1).evaluate(a=>a.pause());assert.equal(await audio.nth(1).evaluate(a=>a.paused),true);assert.deepEqual(errors,[]);pass=true;
 await writeFile(out+'/result.json',JSON.stringify({pass,explicit_native_playback:true,no_idle_mp3:true,seek_both_to_same_phrase:true,clickable_phrase_before_play:true,phrase_click_pauses_both:true,one_at_a_time:true,widths:[1280,390,320],no_js_native_controls:true,guide_moments:data.changes.length,errors},null,2)+'\n');
 console.log(JSON.stringify({pass,seek,guide_moments:data.changes.length}));
} catch(error){diagnostic=String(error);await writeFile(out+'/failure.json',JSON.stringify({pass,diagnostic,errors,requests},null,2)+'\n');console.error(JSON.stringify({pass,diagnostic,errors,requests}));throw error;}
finally {await browser.close();}
