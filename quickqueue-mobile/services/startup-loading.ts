const STARTUP_LOADING_DURATION_MS = 9000;
const startupBeganAt = Date.now();

/** Keep the branded loader visible for at least nine seconds from app startup. */
export function waitForStartupLoadingWindow() {
  const remaining = Math.max(0, STARTUP_LOADING_DURATION_MS - (Date.now() - startupBeganAt));
  return new Promise<void>((resolve) => setTimeout(resolve, remaining));
}

export function getStartupElapsedMs() {
  return Date.now() - startupBeganAt;
}
