import { createPlayer } from './player.js';
import { createSleepTimer } from './sleep-timer.js';
import { createBroadcastContext } from './broadcast-context.js';

// A late module must not replace listening already started with native controls.
function initialize() {
  const native = document.querySelector('#native-stream');
  if (!native.paused || native.played.length > 0) return;
  const audio = document.querySelector('#stream');
  const button = document.querySelector('#toggle');
  const label = document.querySelector('#toggle-label');
  const status = document.querySelector('#playback-status');
  const panel = document.querySelector('#player');
  const live = document.querySelector('#live-label');
  const volume = document.querySelector('#volume');
  const volumeValue = document.querySelector('#volume-value');
  const activeStates = new Set(['connecting', 'playing', 'buffering', 'retrying']);
  let active = false, gain = 1, requestedVolume = Number(volume.value) / 100;
  let volumeSupported = true, player, playing = false;
  const broadcastPanel = document.querySelector('#broadcast-context');
  const broadcastTitle = document.querySelector('#broadcast-context-title');
  const broadcast = createBroadcastContext({onChange(title) {
    if (!broadcastPanel || !broadcastTitle) return;
    broadcastTitle.textContent = title || '';
    broadcastPanel.hidden = title === null;
  }});
  function syncBroadcast() {
    broadcast.setEnabled(playing && !document.hidden && Boolean(broadcastPanel && broadcastTitle));
  }
  const timerSelect = document.querySelector('#sleep-timer');
  const timerRemaining = document.querySelector('#timer-remaining');
  const timerStatus = document.querySelector('#timer-status');
  function applyVolume(force = false) {
    if (!player || (!volumeSupported && !force)) return;
    volumeSupported = player.setVolume(requestedVolume * gain);
    document.querySelector('#volume-control').hidden = !volumeSupported;
    document.querySelector('#volume-note').hidden = volumeSupported;
  }
  const timer = createSleepTimer({
    onGain(value) {
      const restoring = value === 1 && gain < 1;
      gain = value;
      applyVolume(restoring);
    },
    onExpire() { player.pause(); },
    onChange(value) {
      timerSelect.value = String(value.minutes);
      timerRemaining.hidden = value.phase !== 'running';
      const seconds = value.remainingSeconds;
      timerRemaining.textContent = `Stops in ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
      const message = value.phase === 'expired' ? 'Timer ended. Rest well.'
        : value.phase === 'armed' ? 'Starts when you press play.'
        : value.phase === 'running' ? 'Timer set. Keep this page open.'
        : 'Stops playback on this device. Keep this page open.';
      if (timerStatus.textContent !== message) timerStatus.textContent = message;
    }
  });
  timerSelect.addEventListener('change', () => timer.setMinutes(Number(timerSelect.value)));
  document.addEventListener('visibilitychange', () => { timer.refresh(); syncBroadcast(); });

  player = createPlayer(audio, {
    onChange(value) {
      active = activeStates.has(value.state);
      playing = value.state === 'playing';
      syncBroadcast();
      timer.setActive(active);
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
    requestedVolume = Number(volume.value) / 100;
    applyVolume(true);
    volumeValue.textContent = `${volume.value}%`;
    volume.setAttribute('aria-valuetext', `${volume.value} percent`);
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
  window.addEventListener('pagehide', () => { player.pause(); timer.setMinutes(0); broadcast.setEnabled(false); });

  // Keep the independent native player available until all setup has succeeded.
  native.removeAttribute('src');
  native.load();
  document.querySelector('#native-fallback').hidden = true;
  document.querySelector('#enhanced-controls').hidden = false;
}
initialize();
