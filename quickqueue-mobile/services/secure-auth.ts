import * as SecureStore from "expo-secure-store";

export type BiometricKind = "fingerprint" | "face";

const refreshKey = "quickqueue.biometricRefreshToken";
const enabledKey = (kind: BiometricKind) => `quickqueue.${kind}Enabled`;

export const enableBiometricLogin = async (kind: BiometricKind, refreshToken: string) => {
  await SecureStore.setItemAsync(refreshKey, refreshToken);
  await SecureStore.setItemAsync(enabledKey(kind), "true");
};

export const updateBiometricRefreshToken = async (refreshToken: string) => {
  const [fingerprint, face] = await Promise.all([
    SecureStore.getItemAsync(enabledKey("fingerprint")),
    SecureStore.getItemAsync(enabledKey("face")),
  ]);
  if (fingerprint === "true" || face === "true") {
    await SecureStore.setItemAsync(refreshKey, refreshToken);
  }
};

export const getBiometricLogin = async (kind: BiometricKind) => {
  const [enabled, refreshToken] = await Promise.all([
    SecureStore.getItemAsync(enabledKey(kind)),
    SecureStore.getItemAsync(refreshKey),
  ]);
  return { enabled: enabled === "true", refreshToken };
};

export const disableBiometricLogin = async (kind: BiometricKind) => {
  await SecureStore.deleteItemAsync(enabledKey(kind));
  const otherKind: BiometricKind = kind === "fingerprint" ? "face" : "fingerprint";
  const otherEnabled = await SecureStore.getItemAsync(enabledKey(otherKind));
  if (otherEnabled !== "true") await SecureStore.deleteItemAsync(refreshKey);
};

export const getBiometricStatuses = async () => {
  const [fingerprint, face] = await Promise.all([
    SecureStore.getItemAsync(enabledKey("fingerprint")),
    SecureStore.getItemAsync(enabledKey("face")),
  ]);
  return { fingerprint: fingerprint === "true", face: face === "true" };
};
