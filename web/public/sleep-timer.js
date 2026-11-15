/** Personal listening deadline. It never opens or owns a media connection. */
export function createSleepTimer(options = {}) {
  const now = options.now || Date.now;
  const schedule = options.setTimeout || globalThis.setTimeout.bind(globalThis);
  const cancel = options.clearTimeout || globalThis.clearTimeout.bind(globalThis);
  const onChange = options.onChange || (() => {});
  const onGain = options.onGain || (() => {});
  const onExpire = options.onExpire || (() => {});
  let minutes = 0, active = false, disposed = false, generation = 0, phase = 'off';
  let deadline, pending;

  function clearTick() {
    generation++;
    if (pending !== undefined) cancel(pending);
    pending = undefined;
  }
  function emit(next, remainingSeconds = minutes * 60) {
    phase = next;
    onChange({ minutes, remainingSeconds, phase });
  }
  function tick(token) {
    if (disposed || token !== generation || deadline === undefined) return;
    pending = undefined;
    const remaining = Math.max(0, deadline - now());
    if (!remaining) {
      clearTick();
      minutes = 0; deadline = undefined; active = false;
      onGain(0);
      emit('expired', 0);
      try { onExpire(); } finally { onGain(1); }
      return;
    }
    onGain(Math.min(1, remaining / 20000));
    emit('running', Math.ceil(remaining / 1000));
    pending = schedule(() => tick(token), Math.min(1000, remaining));
  }
  function refresh() {
    if (disposed) return;
    clearTick();
    if (deadline !== undefined) tick(generation);
    else if (phase !== 'expired') emit(minutes ? 'armed' : 'off');
  }
  const api = {
    setMinutes(value) {
      if (disposed || ![0, 15, 30, 60].includes(value)) return false;
      clearTick();
      minutes = value;
      phase = 'off';
      deadline = active && minutes ? now() + minutes * 60000 : undefined;
      onGain(1);
      refresh();
      return true;
    },
    setActive(value) {
      if (disposed) return;
      if (!value) {
        active = false;
        if (minutes) api.setMinutes(0);
      } else if (!active) {
        active = true;
        phase = 'off';
        if (minutes) deadline = now() + minutes * 60000;
        refresh();
      }
    },
    refresh,
    dispose() {
      if (disposed) return;
      api.setMinutes(0);
      disposed = true;
    }
  };
  emit('off');
  return api;
}
