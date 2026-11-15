/** Wrap an async callback so a slow call is never started again while it still runs. */
export function noOverlap(callback) {
  let inFlight = false
  return async (...args) => {
    if (inFlight) return
    inFlight = true
    try {
      return await callback(...args)
    } finally {
      inFlight = false
    }
  }
}

/** Create an idempotent, non-overlapping interval owner. */
export function createPoller(callback, intervalMs, options = {}) {
  const setIntervalFn = options.setIntervalFn || globalThis.setInterval
  const clearIntervalFn = options.clearIntervalFn || globalThis.clearInterval
  let timer = null
  let inFlight = false

  const tick = async () => {
    if (inFlight) return
    inFlight = true
    try {
      await callback()
    } finally {
      inFlight = false
    }
  }

  return {
    start({ immediate = false } = {}) {
      if (timer !== null) return
      if (immediate) void tick()
      timer = setIntervalFn(tick, intervalMs)
    },
    stop() {
      if (timer === null) return
      clearIntervalFn(timer)
      timer = null
    },
    isRunning() {
      return timer !== null
    },
    tick,
  }
}
