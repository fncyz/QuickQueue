const DEFAULT_API_BASE_URL = "https://quick-queue-virid.vercel.app/api";

export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_BASE_URL)
  .replace(/\/+$/, "");
