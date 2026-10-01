// Keep the branded startup animation visible briefly, but never impose more
// than a nine-second startup window.
const STARTUP_LOADING_DURATION_MS = 9000;
const startupBeganAt = Date.now();

/** Uses one app-wide clock so nested startup checks never add multiple delays. */
export function waitForStartupLoadingWindow() {
  const remaining = Math.max(0, STARTUP_LOADING_DURATION_MS - (Date.now() - startupBeganAt));
  return new Promise<void>((resolve) => setTimeout(resolve, remaining));
}

export function getStartupElapsedMs() {
  return Date.now() - startupBeganAt;
}
