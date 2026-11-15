import test from 'node:test';
import assert from 'node:assert/strict';
let createBroadcastContext;
try { ({createBroadcastContext}=await import('../public/broadcast-context.js')); }
catch(error) { if(error.code!=='ERR_MODULE_NOT_FOUND') throw error; }

const settle=()=>new Promise(resolve=>setImmediate(resolve));
const packet=(title='Generative Radio - Chapter 78 is unfolding. Warm keys.')=>({version:1,available:true,title});
const response=value=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
function fixture(behavior=()=>response(packet())) {
  assert.equal(typeof createBroadcastContext,'function','bounded broadcast context controller is missing');
  let time=0,id=0;const jobs=new Map(),calls=[],changes=[];
  const context=createBroadcastContext({now:()=>time,
    schedule(fn,delay){const key=++id;jobs.set(key,{fn,at:time+delay});return key;},
    cancel(key){jobs.delete(key);},
    fetcher(url,options){calls.push({url,options,at:time});return behavior(calls.length,options);},
    onChange:value=>changes.push(value)});
  return {context,calls,changes,jobs,value:()=>changes.at(-1)??null,
    jump(ms){time+=ms;},
    async due(){
      for(let n=0;n<100;n++) {
        const next=[...jobs].filter(([,j])=>j.at<=time).sort((a,b)=>a[1].at-b[1].at)[0];
        if(!next) return;
        jobs.delete(next[0]);next[1].fn();await settle();
      }
      assert.fail('unbounded scheduled work');
    },
    async advance(ms){
      const end=time+ms;
      for(let n=0;n<100;n++) {
        const next=[...jobs].sort((a,b)=>a[1].at-b[1].at)[0];
        if(!next||next[1].at>end) {time=end;await settle();return;}
        time=next[1].at;jobs.delete(next[0]);next[1].fn();await settle();
      }
      assert.fail('unbounded scheduled work');
    }};
}

test('context opens no request until enabled; uses one fixed private-free public URL',async()=>{
  const f=fixture();await f.advance(50000);assert.equal(f.calls.length,0);
  f.context.setEnabled(true);await f.advance(0);assert.equal(f.calls.length,1);
  const {url,options}=f.calls[0];assert.equal(url,'/broadcast.json');
  assert.equal(options.cache,'no-store');assert.equal(options.credentials,'omit');assert.equal(options.mode,'same-origin');assert.equal(options.redirect,'error');
  assert.equal(f.value(),'Chapter 78 is unfolding. Warm keys.');
  await f.advance(9999);assert.equal(f.calls.length,1);
  await f.advance(1);assert.equal(f.calls.length,2);f.context.dispose();assert.equal(f.jobs.size,0);
});

test('disable clears owned work and resume honors cooldown without replaying stale data',async()=>{
  const f=fixture();f.context.setEnabled(true);await f.advance(0);
  f.context.setEnabled(false);assert.equal(f.value(),null);assert.equal(f.jobs.size,0);
  await f.advance(1000);f.context.setEnabled(true);await f.advance(8999);assert.equal(f.calls.length,1);assert.equal(f.value(),null);
  await f.advance(1);assert.equal(f.calls.length,2);assert.ok(f.value());f.context.dispose();
});

test('a late result after pause cannot revive details or alter a later session',async()=>{
  let resolveOld;const old=new Promise(resolve=>{resolveOld=resolve;});
  const f=fixture(n=>n===1?old:response(packet('New chapter')));
  f.context.setEnabled(true);await f.advance(0);f.context.setEnabled(false);
  assert.equal(f.calls[0].options.signal.aborted,true);assert.equal(f.jobs.size,0);
  await f.advance(10000);f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),'New chapter');
  resolveOld(response(packet('Old chapter')));await settle();assert.equal(f.value(),'New chapter');f.context.dispose();
});

test('deadline aborts a hung request and releases its slot even if fetch ignores abort',async()=>{
  const f=fixture(n=>n===1?new Promise(()=>{}):response(packet()));f.context.setEnabled(true);await settle();
  await f.advance(2999);assert.equal(f.calls[0].options.signal.aborted,false);
  await f.advance(1);assert.equal(f.calls[0].options.signal.aborted,true);assert.equal(f.value(),null);
  await f.advance(7000);assert.equal(f.calls.length,2);assert.ok(f.value());f.context.dispose();assert.equal(f.jobs.size,0);
});

test('polling never overlaps a current request or accelerates on rapid toggles',async()=>{
  const f=fixture(()=>new Promise(()=>{}));f.context.setEnabled(true);
  for(let n=0;n<20;n++) {f.context.setEnabled(false);f.context.setEnabled(true);await f.advance(100);}
  assert.equal(f.calls.length,1);await f.advance(7999);assert.equal(f.calls.length,1);
  await f.advance(1);assert.equal(f.calls.length,2);f.context.dispose();assert.equal(f.jobs.size,0);
});

test('late work clears data older than15 seconds before a new response arrives',async()=>{
  const f=fixture(n=>n===1?response(packet()):new Promise(()=>{}));f.context.setEnabled(true);await f.advance(0);assert.ok(f.value());
  f.jump(20000);await f.due();assert.equal(f.value(),null);assert.equal(f.calls.length,2);f.context.dispose();
});

test('streamed body limit cancels oversized data even without Content-Length',async()=>{
  let cancelled=false;
  const f=fixture(()=>new Response(new ReadableStream({start(c){c.enqueue(new Uint8Array(4097));},cancel(){cancelled=true;}}),{headers:{'Content-Type':'application/json'}}));
  f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),null);assert.equal(cancelled,true);f.context.dispose();
});

test('a hung response body is cancelled at the overall deadline',async()=>{
  let cancelled=false;
  const f=fixture(()=>new Response(new ReadableStream({cancel(){cancelled=true;}}),{headers:{'Content-Type':'application/json'}}));
  f.context.setEnabled(true);await settle();await f.advance(3000);assert.equal(cancelled,true);assert.equal(f.value(),null);f.context.dispose();assert.equal(f.jobs.size,0);
});

test('exactly4KiB valid payload and160 Unicode codepoints are accepted',async()=>{
  const unicode='😀'.repeat(160);const text=JSON.stringify(packet(unicode));const bytes=new TextEncoder().encode(text);
  const data=new Uint8Array(4096).fill(32);data.set(bytes);
  const f=fixture(()=>new Response(data,{headers:{'Content-Type':'application/json'}}));f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),unicode);f.context.dispose();
});

test('unknown malformed unavailable and oversized labels hide details',async()=>{
  for(const value of [null,[],{},packet(' '),{...packet(),version:2},{...packet(),available:false},
    {...packet(),available:'true'},packet(12),packet('x'.repeat(161)),packet('😀'.repeat(161)),{...packet(),private:'unexpected'}]) {
    const f=fixture(()=>response(value));f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),null,JSON.stringify(value));f.context.dispose();
  }
});

test('HTTP/MIME/JSON/invalid UTF8 failures stay optional and retry at a bounded rate',async()=>{
  const badBytes=new Uint8Array([...new TextEncoder().encode('{"version":1,"available":true,"title":"'),255,...new TextEncoder().encode('"}')]);
  for(const bad of [()=>new Response('no',{status:503}),()=>new Response('{}'),
    ()=>new Response('not JSON',{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(badBytes,{headers:{'Content-Type':'application/json'}}),()=>Promise.reject(new Error('offline'))]) {
    const f=fixture(n=>n===1?bad():response(packet()));f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),null);
    await f.advance(9999);assert.equal(f.calls.length,1);await f.advance(1);assert.ok(f.value());f.context.dispose();
  }
});

test('labels remain literal text and only exact station prefix is removed',async()=>{
  for(const title of ['<img src=x onerror=alert(1)>','Other artist - Song','Generative Radio-ish']) {
    const f=fixture(()=>response(packet(title)));f.context.setEnabled(true);await f.advance(0);assert.equal(f.value(),title);f.context.dispose();
  }
});

test('a stale queued callback cannot erase ownership of a newer session timer',async()=>{
  const f=fixture();f.context.setEnabled(true);const stale=[...f.jobs.values()][0].fn;
  f.context.setEnabled(false);f.context.setEnabled(true);stale();
  f.context.setEnabled(false);assert.equal(f.jobs.size,0);await f.advance(20000);assert.equal(f.calls.length,0);
});

test('disposal prevents future work while ordinary disable remains resumable',async()=>{
  const f=fixture();f.context.setEnabled(true);await f.advance(0);f.context.dispose();f.context.setEnabled(true);await f.advance(50000);
  assert.equal(f.calls.length,1);assert.equal(f.value(),null);assert.equal(f.jobs.size,0);
});
