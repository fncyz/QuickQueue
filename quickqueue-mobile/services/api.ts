import axios from "axios";

import { API_BASE_URL } from "@/src/config/api";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/`,
  headers: {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
  },
});

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
