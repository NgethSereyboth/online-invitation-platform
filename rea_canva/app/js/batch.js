// Frame-aligned input batching: continuous gestures merge their deltas and
// commit at most once per animation frame (the central trick in the Canva study).

export function createFrameBatcher(reduce, commit) {
  let pending = null;
  let handle = 0;

  function flush() {
    if (!pending) return;
    cancelAnimationFrame(handle);
    handle = 0;
    const value = pending.value;
    pending = null;
    commit(value);
  }

  return {
    accumulate(value) {
      if (pending) {
        pending.value = reduce(pending.value, value);
        return;
      }
      pending = { value };
      handle = requestAnimationFrame(() => {
        handle = 0;
        flush();
      });
    },
    flush,
    get pending() {
      return Boolean(pending);
    },
  };
}

export const debounce = (fn, wait = 200) => {
  let timer = 0;
  const wrapped = (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
  wrapped.cancel = () => window.clearTimeout(timer);
  return wrapped;
};
