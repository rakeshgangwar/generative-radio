import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../public/style.css',import.meta.url),'utf8');
function color(name){return css.match(new RegExp(`--${name}: (#[0-9a-f]{6})`))[1];}
function luminance(hex){
  const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
  return rgb.reduce((sum,c,i)=>sum+c*[.2126,.7152,.0722][i],0);
}
test('small body/status/control copy meets WCAG AA text contrast',()=>{
  for(const [foreground,background] of [['slate','mist'],['ink','mist'],['sea','mist'],['paper','ink']]){
    const [a,b]=[luminance(color(foreground)),luminance(color(background))].sort((a,b)=>a-b);
    assert.ok((b+.05)/(a+.05)>=4.5,`${foreground} on ${background} needs 4.5:1`);
  }
});
const html=readFileSync(new URL('../public/index.html',import.meta.url),'utf8');
test('custom controls start hidden until JavaScript works; native fallback stays available',()=>{
  assert.match(html, /id="enhanced-controls" hidden/);
  assert.match(html, /<noscript>[\s\S]*<audio controls/);
});
test('working volume control is not described by hidden device-volume fallback',()=>{
  assert.doesNotMatch(html, /<input[^>]*aria-describedby="volume-note"/);
});
