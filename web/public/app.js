import { createPlayer } from './player.js';

const audio = document.querySelector('#stream');
const button = document.querySelector('#toggle');
const label = document.querySelector('#toggle-label');
const status = document.querySelector('#playback-status');
const panel = document.querySelector('#player');
const live = document.querySelector('#live-label');
const volume = document.querySelector('#volume');
const volumeValue = document.querySelector('#volume-value');
const activeStates = new Set(['connecting', 'playing', 'buffering', 'retrying']);
let active = false;

const player = createPlayer(audio, {
  onChange(value) {
    active = activeStates.has(value.state);
    panel.dataset.state = value.state;
    document.body.dataset.playing = String(value.state === 'playing');
    label.textContent = active ? 'Pause' : value.state === 'error' ? 'Try again' : value.state === 'paused' ? 'Resume listening' : 'Start listening';
    status.textContent = value.message;
    live.hidden = value.state !== 'playing';
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = value.state === 'playing' ? 'playing' : 'paused';
    }
  }
});
button.addEventListener('click', () => active ? player.pause() : player.start());
function setVolume() {
  const value = Number(volume.value) / 100;
  const controlled = player.setVolume(value);
  volumeValue.textContent = `${volume.value}%`;
  volume.setAttribute('aria-valuetext', `${volume.value} percent`);
  if (!controlled) {
    document.querySelector('#volume-control').hidden = true;
    document.querySelector('#volume-note').hidden = false;
  }
}
volume.addEventListener('input', setVolume);
setVolume();

if ('mediaSession' in navigator) {
  if ('MediaMetadata' in window) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: 'Generative Radio', artist: 'Original ambient music', album: 'Live stream'
    });
  }
  for (const [action, handler] of Object.entries({play: () => player.start(), pause: () => player.pause(), stop: () => player.pause()})) {
    try { navigator.mediaSession.setActionHandler(action, handler); } catch { /* Optional platform capability. */ }
  }
}
window.addEventListener('pagehide', () => player.pause());
