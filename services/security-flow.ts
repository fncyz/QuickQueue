import type { Href } from "expo-router";

export const securitySetupRoute = (stage: string | null, registrationPending = false): Href => {
  if (stage === "password") return "/set-password";
  if (stage === "pin") return "/set-pin";
  if (stage === "fingerprint") return "/setup-fingerprint";
  if (stage === "face") return "/setup-face";
  if (stage === "complete" && registrationPending) return "/registration-complete";
  return "/(tabs)";
};
