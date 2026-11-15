import test from 'node:test';
import assert from 'node:assert/strict';
import {createSleepTimer} from '../public/sleep-timer.js';

function fixture() {
  let time=100000, id=0, expired=0;
  const timers=new Map(), callbacks=[], changes=[], gains=[];
  const timer=createSleepTimer({now:()=>time,
    setTimeout(fn,delay){const key=++id;timers.set(key,{fn,at:time+delay});callbacks.push(fn);return key;},
    clearTimeout(key){timers.delete(key);},
    onChange:value=>changes.push(value),onGain:value=>gains.push(value),onExpire:()=>expired++});
  return {timer,timers,callbacks,changes,gains,get expired(){return expired;},
    last:()=>changes.at(-1),gain:()=>gains.at(-1),
    jump(ms){time+=ms;},
    tick(){const next=[...timers].filter(([,t])=>t.at<=time).sort((a,b)=>a[1].at-b[1].at)[0];if(next){timers.delete(next[0]);next[1].fn();}},
  };
}

test('timer defaults off and rejects unsupported durations without side effects',()=>{
  const f=fixture();assert.equal(f.last().phase,'off');assert.equal(f.timers.size,0);
  for(const value of [1,-1,NaN,Infinity,'15',null])assert.equal(f.timer.setMinutes(value),false);
  assert.equal(f.last().minutes,0);assert.equal(f.expired,0);assert.equal(f.timers.size,0);
});
test('idle selection arms without playback and starts at the next explicit active session',()=>{
  const f=fixture();f.timer.setMinutes(15);assert.equal(f.last().phase,'armed');assert.equal(f.timers.size,0);
  f.jump(1200000);f.timer.refresh();assert.equal(f.expired,0);
  f.timer.setActive(true);assert.equal(f.last().remainingSeconds,900);
  f.jump(899000);f.tick();assert.equal(f.expired,0);assert.equal(f.last().remainingSeconds,1);
  f.jump(1000);f.tick();assert.equal(f.expired,1);assert.equal(f.last().phase,'expired');assert.equal(f.last().minutes,0);
});
test('a delayed background tick expires from the deadline, not tick count',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(30);f.jump(1900000);f.tick();
  assert.equal(f.expired,1);assert.equal(f.timers.size,0);f.timer.refresh();assert.equal(f.expired,1);
});
test('active reconnect updates never restart the deadline',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);f.jump(600000);
  for(let n=0;n<10;n++)f.timer.setActive(true);
  f.timer.refresh();assert.equal(f.last().remainingSeconds,300);
  f.jump(300000);f.tick();assert.equal(f.expired,1);
});
test('the final twenty seconds fade monotonically and restore gain after expiry',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);assert.equal(f.gain(),1);
  f.jump(880000);f.tick();assert.equal(f.gain(),1);
  f.jump(10000);f.tick();assert.equal(f.gain(),.5);
  f.jump(9000);f.tick();assert.equal(f.gain(),.05);
  f.jump(1000);f.tick();assert.equal(f.expired,1);assert.equal(f.gain(),1);assert.ok(f.gains.includes(0));
});
test('Off cancels fading and a queued stale tick cannot affect a later timer',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);const stale=f.callbacks.at(-1);
  f.jump(890000);f.tick();assert.equal(f.gain(),.5);
  f.timer.setMinutes(0);assert.equal(f.gain(),1);assert.equal(f.timers.size,0);
  f.timer.setMinutes(60);stale();assert.equal(f.expired,0);assert.equal(f.last().remainingSeconds,3600);
});
test('manual pause cancels the timer and explicit resume does not rearm it',()=>{
  const f=fixture();f.timer.setMinutes(15);f.timer.setActive(true);const stale=f.callbacks.at(-1);
  f.timer.setActive(false);assert.equal(f.last().phase,'off');assert.equal(f.last().minutes,0);
  f.jump(900000);f.timer.setActive(true);stale();assert.equal(f.expired,0);assert.equal(f.timers.size,0);
});
test('selecting a new duration restarts from now and clears the fade',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);f.jump(890000);f.tick();
  f.timer.setMinutes(30);assert.equal(f.last().remainingSeconds,1800);assert.equal(f.gain(),1);
  f.jump(900000);f.tick();assert.equal(f.expired,0);
});
test('disposal cancels armed and scheduled work permanently',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);const stale=f.callbacks.at(-1);
  f.timer.dispose();f.jump(900000);stale();f.timer.setActive(true);f.timer.setMinutes(15);f.timer.refresh();
  assert.equal(f.expired,0);assert.equal(f.timers.size,0);assert.equal(f.gain(),1);
});
test('an explicit inactive lifecycle cancels a timer armed before playback',()=>{
  const f=fixture();f.timer.setMinutes(15);f.timer.setActive(false);
  assert.equal(f.last().phase,'off');f.timer.setActive(true);assert.equal(f.timers.size,0);
});
test('a visibility refresh preserves expiry until the next explicit action',()=>{
  const f=fixture();f.timer.setActive(true);f.timer.setMinutes(15);f.jump(900000);f.tick();
  f.timer.refresh();assert.equal(f.last().phase,'expired');
  f.timer.setMinutes(0);assert.equal(f.last().phase,'off');
});
