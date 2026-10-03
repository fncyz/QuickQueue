const startupBeganAt = Date.now();

export function getStartupElapsedMs() {
  return Date.now() - startupBeganAt;
}
