/** Optional broadcast labels. This module never controls audio playback. */
const BYTE_LIMIT = 4096;
const INTERVAL = 10000;
const DEADLINE = 3000;
const FRESHNESS = 15000;

function cancelBody(body) {
  try { Promise.resolve(body?.cancel()).catch(() => {}); } catch { /* Already closed/locked. */ }
}

async function readLabel(response, signal) {
  if (signal.aborted || !response.ok ||
      !/^application\/json(?:\s*;|$)/i.test(response.headers.get('Content-Type') || '')) {
    cancelBody(response.body);
    throw new Error('Context response unavailable');
  }
  const length = response.headers.get('Content-Length');
  if (length && /^\d+$/.test(length) && Number(length) > BYTE_LIMIT) {
    cancelBody(response.body);
    throw new Error('Context body is too large');
  }
  if (!response.body?.getReader) throw new Error('Context body streaming is unavailable');
  const reader = response.body.getReader(), chunks = [];
  let size = 0;
  const abort = () => {
    try { Promise.resolve(reader.cancel()).catch(() => {}); } catch { /* Already closed. */ }
  };
  signal.addEventListener('abort', abort, {once:true});
  try {
    while (true) {
      if (signal.aborted) throw new Error('Context request cancelled');
      const {value, done} = await reader.read();
      if (done) break;
      if (!(value instanceof Uint8Array) || size + value.byteLength > BYTE_LIMIT) {
        abort();
        throw new Error('Invalid or oversized context body');
      }
      size += value.byteLength;
      chunks.push(value);
    }
    if (signal.aborted) throw new Error('Context request cancelled');
  } finally {
    signal.removeEventListener('abort', abort);
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  const value = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join(',') !== 'available,title,version' ||
      value.version !== 1 || typeof value.available !== 'boolean' ||
      typeof value.title !== 'string' || [...value.title].length > 160) {
    throw new Error('Invalid context schema');
  }
  if (!value.available) return null;
  const prefix = 'Generative Radio - ';
  const title = (value.title.startsWith(prefix) ? value.title.slice(prefix.length) : value.title).trim();
  return title || null;
}

export function createBroadcastContext(options = {}) {
  const fetcher = options.fetcher ?? globalThis.fetch;
  const now = options.now || (() => globalThis.performance?.now() ?? Date.now());
  const schedule = options.schedule || globalThis.setTimeout.bind(globalThis);
  const cancel = options.cancel || globalThis.clearTimeout.bind(globalThis);
  const onChange = options.onChange || (() => {});
  const supported = typeof fetcher === 'function' && typeof AbortController === 'function' &&
    typeof TextDecoder === 'function';
  let enabled = false, disposed = false, generation = 0, poll, current;
  let nextStart = -Infinity, freshAt = -Infinity, visible = null;

  function display(value) {
    if (visible === value) return;
    visible = value;
    // Optional programme details must not break the main audio controls.
    try { onChange(value); } catch { /* Subscriber failure is isolated. */ }
  }
  function expire() {
    if (visible !== null && now() - freshAt >= FRESHNESS) display(null);
  }
  function clearDeadline(request) {
    if (request.timer !== undefined) cancel(request.timer);
    request.timer = undefined;
  }
  function abortRequest(request) {
    clearDeadline(request);
    request.controller.abort();
    request.reject(new Error('Context request cancelled'));
  }
  function queue() {
    if (!enabled || disposed || current || poll !== undefined) return;
    const token = generation;
    poll = schedule(() => {
      if (token !== generation) return;
      poll = undefined;
      if (enabled && !disposed) run(token);
    }, Math.max(0, nextStart - now()));
  }
  async function run(token) {
    if (!enabled || disposed || token !== generation || current) return;
    expire();
    if (now() < nextStart) { queue(); return; }
    nextStart = now() + INTERVAL;
    const request = {controller:new AbortController(), timer:undefined, reject:null};
    const cancelled = new Promise((_, reject) => { request.reject = reject; });
    current = request;
    request.timer = schedule(() => { request.timer = undefined; abortRequest(request); }, DEADLINE);
    try {
      const work = (async () => {
        const response = await fetcher('/broadcast.json', {
          signal:request.controller.signal, cache:'no-store', credentials:'omit',
          mode:'same-origin', redirect:'error', headers:{Accept:'application/json'}
        });
        return readLabel(response, request.controller.signal);
      })();
      const title = await Promise.race([work, cancelled]);
      if (enabled && !disposed && token === generation) {
        freshAt = now();
        display(title);
      }
    } catch {
      request.controller.abort();
      if (enabled && !disposed && token === generation) display(null);
    } finally {
      clearDeadline(request);
      if (current === request) current = undefined;
      if (enabled && !disposed && token === generation) queue();
    }
  }
  function setEnabled(value) {
    if (disposed) return;
    const next = value === true && supported;
    expire();
    if (next === enabled) return;
    enabled = next;
    generation++;
    if (poll !== undefined) cancel(poll);
    poll = undefined;
    if (current) { const request = current; current = undefined; abortRequest(request); }
    display(null);
    if (enabled) queue();
  }
  function dispose() {
    setEnabled(false);
    disposed = true;
  }
  return {setEnabled, dispose};
}
