import test from 'node:test';
import assert from 'node:assert/strict';
import { createPlayer } from '../public/player.js';

class Media extends EventTarget {
  src = ''; paused = true; ended = false; volume = 1; loads = 0;
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; this.dispatchEvent(new Event('pause')); }
  load() { this.loads++; }
  removeAttribute(name) { if (name === 'src') this.src = ''; }
  emit(name) { if(name === 'playing') this.paused = false; this.dispatchEvent(new Event(name)); }
}
function fixture() {
  let time = 0, next = 0;
  const jobs = new Map(), states = [], audio = new Media();
  const player = createPlayer(audio, {
    source: '/radio.mp3', onChange: value => states.push(value), now: () => time,
    setTimeout: (fn, delay) => { jobs.set(++next, {fn, at:time+delay}); return next; },
    clearTimeout: id => jobs.delete(id)
  });
  const tick = ms => {
    const end = time + ms;
    while(true) {
      const first = [...jobs].sort((a,b) => a[1].at-b[1].at)[0];
      if(!first || first[1].at > end) break;
      time = first[1].at; jobs.delete(first[0]); first[1].fn();
    }
    time = end;
  };
  return {audio, player, tick, jobs, states, state: () => states.at(-1)};
}
const settle = async () => { await Promise.resolve(); await Promise.resolve(); };

test('no media request until user intent; only real playing means playing', async () => {
  const f=fixture();
  assert.equal(f.audio.src,''); assert.equal(f.audio.loads,0);
  assert.equal(f.state().state,'idle');
  f.player.start(); await settle();
  assert.match(f.audio.src,/^\/radio\.mp3\?/);
  assert.equal(f.state().state,'connecting');
  f.audio.emit('playing'); assert.equal(f.state().state,'playing');
});
test('pause releases the stream and cancels every recovery timer', () => {
  const f=fixture(); f.player.start(); f.audio.emit('error');
  assert.equal(f.state().state,'retrying');
  f.player.pause(); f.tick(100000);
  assert.equal(f.state().state,'paused'); assert.equal(f.audio.src,'');
  assert.equal(f.jobs.size,0); assert.equal(f.audio.paused,true);
});
test('late rejection and playing events cannot revive paused playback', async () => {
  const f=fixture(); let reject;
  f.audio.play=() => new Promise((_,no) => {reject=no;});
  f.player.start(); f.player.pause(); reject(new Error('old source')); await settle();
  f.audio.emit('playing');
  assert.equal(f.state().state,'paused'); assert.equal(f.jobs.size,0);
});
test('old play promise cannot fail a newer connection', async () => {
  const f=fixture(); let reject;
  f.audio.play=() => new Promise((_,no) => {reject=no;});
  f.player.start(); f.player.pause();
  f.audio.play=() => Promise.resolve(); f.player.start(); f.audio.emit('playing');
  reject(new Error('old source')); await settle();
  assert.equal(f.state().state,'playing');
});
test('connection deadline and three recovery attempts are bounded', () => {
  const f=fixture(); f.player.start(); f.tick(15000);
  assert.equal(f.state().state,'retrying'); assert.equal(f.state().attempt,1);
  f.tick(1000); assert.equal(f.state().state,'connecting');
  f.tick(15000); assert.equal(f.state().attempt,2);
  f.tick(3000+15000); assert.equal(f.state().attempt,3);
  f.tick(8000+15000); assert.equal(f.state().state,'error');
  assert.equal(f.jobs.size,0); assert.equal(f.audio.src,'');
  f.player.start(); assert.equal(f.state().attempt,0);
});
test('short playing/drop loops do not reset the restart budget', () => {
  const f=fixture(); f.player.start();
  for(const delay of [1000,3000,8000]) {
    f.audio.emit('playing'); f.tick(100); f.audio.emit('ended');
    assert.equal(f.state().state,'retrying'); f.tick(delay);
  }
  f.audio.emit('playing'); f.tick(100); f.audio.emit('ended');
  assert.equal(f.state().state,'error');
});
test('thirty seconds of stable playback reset recovery budget', () => {
  const f=fixture(); f.player.start(); f.audio.emit('error'); f.tick(1000);
  f.audio.emit('playing'); f.tick(30000); f.audio.emit('error');
  assert.equal(f.state().attempt,1); assert.equal(f.state().state,'retrying');
});
test('repeated waiting events do not extend a stalled audio deadline', () => {
  const f=fixture(); f.player.start(); f.audio.emit('playing');
  f.audio.emit('waiting'); assert.equal(f.state().state,'buffering');
  f.tick(10000); f.audio.emit('waiting'); f.tick(5000);
  assert.equal(f.state().state,'retrying');
});
test('repeated errors while retrying do not spend extra retry attempts', () => {
  const f=fixture(); f.player.start(); f.audio.emit('error');
  f.audio.emit('error'); f.audio.emit('ended');
  assert.equal(f.state().attempt,1); f.tick(1000);
  assert.equal(f.state().state,'connecting');
});
test('browser permission rejection requires another user gesture', async () => {
  const f=fixture(); f.audio.play=()=>Promise.reject(new DOMException('gesture required','NotAllowedError'));
  f.player.start(); await settle(); f.tick(100000);
  assert.equal(f.state().state,'error'); assert.equal(f.jobs.size,0);
  assert.match(f.state().message,/browser|press|play/i);
});
test('external pause stops intent; ended media still gets recovery', () => {
  const f=fixture(); f.player.start(); f.audio.emit('playing'); f.audio.pause();
  assert.equal(f.state().state,'paused'); assert.equal(f.jobs.size,0);
  f.player.start(); f.audio.emit('playing'); f.audio.ended=true; f.audio.pause();
  assert.equal(f.state().state,'retrying');
});
test('volume clamps and reports platforms that ignore programmatic volume', () => {
  const f=fixture(); assert.equal(f.player.setVolume(.3),true); assert.equal(f.audio.volume,.3);
  f.player.setVolume(2); assert.equal(f.audio.volume,1);
  Object.defineProperty(f.audio,'volume',{get:()=>1,set:()=>{}});
  assert.equal(f.player.setVolume(.2),false);
});
test('dispose removes listeners/timers and prevents future starts', () => {
  const f=fixture(); f.player.start(); f.player.dispose(); const count=f.states.length;
  f.audio.emit('error'); f.audio.emit('playing'); f.player.start(); f.tick(100000);
  assert.equal(f.states.length,count); assert.equal(f.jobs.size,0); assert.equal(f.audio.src,'');
});

test('repeated play intent does not reconnect an already playing source', () => {
  const f=fixture();f.player.start();f.audio.emit('playing');const source=f.audio.src;
  f.player.start();assert.equal(f.state().state,'playing');assert.equal(f.audio.src,source);
});
