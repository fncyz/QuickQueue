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
};

export const loginResident = async (username: string, password: string) => {
  const response = await api.post<LoginResponse>("login/", { username, password });
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
