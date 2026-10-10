import axios, { AxiosError } from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { API_BASE_URL } from "@/src/config/api";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/`,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
  },
});

let refreshInFlight: Promise<string> | null = null;

const requestId = () => `qq-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
const wait = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const retryDelay = (error: AxiosError, attempt: number) => {
  const rawRetryAfter = error.response?.headers?.["retry-after"];
  const retryAfterSeconds = Number(Array.isArray(rawRetryAfter) ? rawRetryAfter[0] : rawRetryAfter);
  if (Number.isFinite(retryAfterSeconds) && retryAfterSeconds >= 0) return Math.min(retryAfterSeconds * 1000, 4000);
  return Math.min(600 * 2 ** attempt + Math.random() * 350, 2500);
};

const isTemporaryFailure = (error: unknown) => {
  if (!axios.isAxiosError(error)) return false;
  if (!error.response) return error.code !== "ERR_CANCELED";
  return [429, 502, 503, 504].includes(error.response.status);
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config as (typeof error.config & { _retried?: boolean }) | undefined;
    const wasAuthenticated = Boolean(request?.headers?.Authorization);
    if (error.response?.status !== 401 || !request || request._retried || !wasAuthenticated || request.url === "token/refresh/") {
      return Promise.reject(error);
    }

    request._retried = true;
    try {
      if (!refreshInFlight) {
        refreshInFlight = AsyncStorage.getItem("quickqueue.refreshToken").then(async (refresh) => {
          if (!refresh) throw error;
          const response = await axios.post<{ access: string; refresh?: string }>(`${API_BASE_URL}/token/refresh/`, { refresh }, { timeout: 15000 });
          const nextRefresh = response.data.refresh;
          await AsyncStorage.multiSet([
            ["quickqueue.accessToken", response.data.access],
            ...(nextRefresh ? [["quickqueue.refreshToken", nextRefresh] as [string, string]] : []),
          ]);
          return response.data.access;
        }).finally(() => { refreshInFlight = null; });
      }
      const access = await refreshInFlight;
      request.headers.Authorization = `Bearer ${access}`;
      return api.request(request);
    } catch (refreshError: any) {
      // Keep the saved session on transient network/server failures. Only an
      // explicit refresh-token rejection proves that the session has expired.
      if (refreshError?.response?.status === 401) {
        await AsyncStorage.multiRemove(["quickqueue.accessToken", "quickqueue.refreshToken"]);
      }
      return Promise.reject(refreshError);
    }
  },
);

export const registerResident = async (data: any) => {
  const response = await api.post("register/", data);
  return response.data;
};

export const getBarangays = async () => {
  const response = await api.get("barangays/");
  return response.data;
};

export type LoginResponse = {
  success: boolean;
  access: string;
  refresh: string;
  resident: { first_name: string; last_name: string; barangay?: string };
  security_setup_stage: SecuritySetupStage;
};

export type SecuritySetupStage = "password" | "pin" | "fingerprint" | "face" | "complete";

export const loginResident = async (username: string, password: string) => {
  const response = await api.post<LoginResponse>("login/", { username, password });
  return response.data;
};

export const loginResidentWithPin = async (username: string, pin: string) => {
  const response = await api.post<LoginResponse>("login/pin/", { username, pin });
  return response.data;
};

export const refreshResidentSession = async (refresh: string) => {
  const response = await api.post<{ access: string; refresh?: string }>("token/refresh/", { refresh });
  return response.data;
};

export const changePassword = async (accessToken: string, currentPassword: string, newPassword: string, confirmPassword: string) => {
  const response = await api.post("change-password/", {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const setInitialPassword = async (accessToken: string, newPassword: string, confirmPassword: string) => {
  const response = await api.post("set-initial-password/", {
    new_password: newPassword,
    confirm_password: confirmPassword,
  }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const setSecurityPin = async (accessToken: string, pin: string) => {
  const response = await api.post("set-security-pin/", { pin }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const verifySecurityPin = async (accessToken: string, pin: string) => {
  const response = await api.post("verify-security-pin/", { pin }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const verifyAccountPassword = async (accessToken: string, password: string) => {
  const response = await api.post("verify-account-password/", { password }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const changeSecurityPin = async (accessToken: string, password: string, newPin: string, confirmPin: string) => {
  const response = await api.post("change-security-pin/", {
    password,
    new_pin: newPin,
    confirm_pin: confirmPin,
  }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export const advanceSecuritySetup = async (accessToken: string, step: "fingerprint" | "face") => {
  const response = await api.post("advance-security-setup/", { step }, { headers: { Authorization: `Bearer ${accessToken}` } });
  return response.data;
};

export type ChatMessage = { role: "assistant" | "resident"; text: string };
export type ChatResponse = { reply: string; suggestions: string[]; source: string; fallback?: boolean; service_status?: "online" | "degraded"; error_code?: string };
export type AssistantHealth = { status: "ready" | "unavailable"; category?: string; retryable?: boolean };

const authenticatedHeaders = (accessToken: string, id = requestId()) => ({
  Authorization: `Bearer ${accessToken}`,
  "X-Request-ID": id,
});

export const getAssistantHealth = async (accessToken: string) => {
  const response = await api.get<AssistantHealth>("chat/health/", {
    headers: authenticatedHeaders(accessToken),
    timeout: 12000,
  });
  return response.data;
};

export const sendChatMessage = async (accessToken: string, message: string, history: ChatMessage[]) => {
  const id = requestId();
  const started = Date.now();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const currentAccessToken = await AsyncStorage.getItem("quickqueue.accessToken") || accessToken;
      const response = await api.post<ChatResponse>("chat/", {
        message,
        history: history.slice(-6),
      }, {
        headers: authenticatedHeaders(currentAccessToken, id),
        timeout: 25000,
      });
      return response.data;
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined;
      console.warn("QuickQueue chat request failed", { attempt: attempt + 1, durationMs: Date.now() - started, location: "chat_api", status: status ?? "network" });
      if (attempt === 1 || !isTemporaryFailure(error)) throw error;
      await wait(retryDelay(error as AxiosError, attempt));
    }
  }
  throw new Error("Chat request retry loop ended unexpectedly");
};
