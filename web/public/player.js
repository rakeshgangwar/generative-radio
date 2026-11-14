/** Live audio lifecycle. No connection is opened until start() is called. */
export function createPlayer(audio, options = {}) {
  const source = options.source || '/radio.mp3';
  const onChange = options.onChange || (() => {});
  const schedule = options.setTimeout || globalThis.setTimeout.bind(globalThis);
  const cancel = options.clearTimeout || globalThis.clearTimeout.bind(globalThis);
  const now = options.now || Date.now;
  const delays = [1000, 3000, 8000];
  let state = 'idle', intent = false, disposed = false, generation = 0, attempt = 0;
  let deadline, retry, stable;

  function emit(next, message) {
    state = next;
    onChange({ state, message, attempt });
  }
  function clearTimers() {
    for (const timer of [deadline, retry, stable]) if (timer !== undefined) cancel(timer);
    deadline = retry = stable = undefined;
  }
  function release() {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
  }
  function armDeadline() {
    if (deadline !== undefined) return;
    deadline = schedule(() => {
      deadline = undefined;
      failed('The station is taking too long to connect. Try again.');
    }, 15000);
  }
  function failed(message = 'The stream is unavailable. Try again in a moment.') {
    if (!intent || disposed || state === 'retrying') return;
    generation++;
    clearTimers();
    if (attempt >= delays.length) {
      intent = false;
      emit('error', message);
      release();
      return;
    }
    const delay = delays[attempt++];
    emit('retrying', `Connection lost. Reconnecting (${attempt} of ${delays.length})…`);
    release();
    retry = schedule(() => { retry = undefined; connect(); }, delay);
  }
  function rejected(error, token) {
    if (!intent || disposed || token !== generation) return;
    if (error?.name === 'NotAllowedError') {
      intent = false;
      generation++;
      clearTimers();
      emit('error', 'Your browser stopped playback. Press play to listen.');
      release();
    } else {
      failed();
    }
  }
  function connect() {
    if (!intent || disposed) return;
    clearTimers();
    const token = ++generation;
    emit('connecting', 'Connecting to the station…');
    audio.src = `${source}${source.includes('?') ? '&' : '?'}listener=${now()}-${token}`;
    audio.load();
    armDeadline();
    try {
      Promise.resolve(audio.play()).catch(error => rejected(error, token));
    } catch (error) {
      rejected(error, token);
    }
  }
  function pause() {
    if (disposed) return;
    intent = false;
    generation++;
    clearTimers();
    emit('paused', 'Paused. Join the live stream when you’re ready.');
    release();
  }
  const listeners = {
    playing() {
      if (!intent || disposed) { audio.pause(); return; }
      if (!['connecting', 'buffering'].includes(state) || audio.paused) return;
      if (deadline !== undefined) cancel(deadline);
      deadline = undefined;
      if (stable !== undefined) cancel(stable);
      emit('playing', 'You’re listening live.');
      stable = schedule(() => { stable = undefined; attempt = 0; }, 30000);
    },
    waiting() {
      if (!intent || disposed || !['playing', 'buffering'].includes(state)) return;
      if (stable !== undefined) cancel(stable);
      stable = undefined;
      emit('buffering', 'Buffering the stream…');
      armDeadline();
    },
    stalled() { listeners.waiting(); },
    error() { failed(); },
    ended() { failed(); },
    pause() {
      if (!intent || !audio.paused || !['connecting', 'playing', 'buffering'].includes(state)) return;
      if (audio.ended || audio.error) failed();
      else pause();
    }
  };
  for (const [event, listener] of Object.entries(listeners)) audio.addEventListener(event, listener);
  emit('idle', 'Ready when you are.');
  return {
    start() {
      if (disposed || intent) return;
      intent = true; attempt = 0;
      connect();
    },
    pause,
    setVolume(value) {
      if (!Number.isFinite(value)) return false;
      value = Math.min(1, Math.max(0, value));
      try { audio.volume = value; } catch { return false; }
      return Math.abs(audio.volume - value) < .01;
    },
    dispose() {
      if (disposed) return;
      pause();
      disposed = true;
      for (const [event, listener] of Object.entries(listeners)) audio.removeEventListener(event, listener);
    }
  };
}
