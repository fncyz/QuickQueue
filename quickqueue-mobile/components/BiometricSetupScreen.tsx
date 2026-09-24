import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import * as LocalAuthentication from "expo-local-authentication";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, ActivityIndicator, Pressable, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import SecuritySetupProgress from "@/components/SecuritySetupProgress";
import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";
import { Text } from "@/components/Typography";
import { advanceSecuritySetup } from "@/services/api";

type Kind = "fingerprint" | "face";
export default function BiometricSetupScreen({ kind }: { kind: Kind }) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const isFingerprint = kind === "fingerprint";
  const next = isFingerprint ? "/setup-face" : "/registration-complete";

  const advance = useCallback(async () => {
    const token = await AsyncStorage.getItem("quickqueue.accessToken");
    if (!token) return router.replace("/login");
    await advanceSecuritySetup(token, kind);
    await AsyncStorage.setItem("quickqueue.securitySetupStage", isFingerprint ? "face" : "complete");
    router.replace(next);
  }, [isFingerprint, kind, next]);

  useEffect(() => { (async () => {
    const hardware = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
    const requested = isFingerprint ? LocalAuthentication.AuthenticationType.FINGERPRINT : LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION;
    const available = hardware && enrolled && types.includes(requested);
    setSupported(available);
    if (!available) {
      try { await advance(); } catch { Alert.alert("Setup could not continue", "Please check your connection and try again."); }
    }
  })(); }, [advance, isFingerprint]);

  const configure = async () => {
    try {
      setSaving(true);
      const result = await LocalAuthentication.authenticateAsync({ promptMessage: isFingerprint ? "Confirm your fingerprint" : "Confirm face recognition", cancelLabel: "Cancel", disableDeviceFallback: true });
      if (result.success) await advance();
    } catch { Alert.alert("Biometric setup failed", "Please try again or choose Not Now."); }
    finally { setSaving(false); }
  };

  if (supported !== true) return <SafeAreaView style={s.safe}><View style={s.loading}><ActivityIndicator color="#0759D9" /><Text style={s.loadingText}>Checking device security…</Text></View></SafeAreaView>;
  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}><SecuritySetupBackdrop /><View style={s.content}>
    <SecuritySetupProgress current={isFingerprint ? 3 : 4} />
    <View style={s.stepIcon}><Ionicons name={isFingerprint ? "finger-print" : "person"} size={27} color="#FFF" /></View>
    <Text style={s.title}>{isFingerprint ? "Enable Fingerprint" : "Face Recognition"}</Text>
    <Text style={s.description}>{isFingerprint ? "Use your fingerprint to securely access your account and make it easier to sign in." : "Look at your device and let us verify your face to complete your setup."}</Text>
    <View style={[s.graphic, !isFingerprint && s.faceGraphic]}>{isFingerprint ? <Ionicons name="finger-print" size={94} color="#1680FF" /> : <><Ionicons name="scan-outline" size={94} color="#1680FF" /><Ionicons name="person" size={57} color="#1680FF" style={s.facePerson} /></>}</View>
    <Pressable disabled={saving} onPress={configure} style={s.button}><Text style={s.buttonText}>{saving ? "Verifying…" : isFingerprint ? "Set Up Fingerprint" : "Set Up Face Recognition"}</Text></Pressable>
    <Pressable disabled={saving} onPress={advance} style={s.skip}><Text style={s.skipText}>Not Now</Text></Pressable>
  </View></SafeAreaView>;
}

const s = StyleSheet.create({ safe: { backgroundColor: "#F8FBFF", flex: 1 }, content: { flex: 1, paddingHorizontal: 22, paddingTop: 45 }, loading: { alignItems: "center", flex: 1, justifyContent: "center" }, loadingText: { color: "#68748A", fontSize: 11, marginTop: 10 }, stepIcon: { alignItems: "center", alignSelf: "center", backgroundColor: "#0645A8", borderRadius: 30, height: 60, justifyContent: "center", marginTop: 3, width: 60 }, title: { color: "#082A72", fontSize: 22, fontWeight: "800", marginTop: 18, textAlign: "center" }, description: { alignSelf: "center", color: "#7083A2", fontSize: 10, lineHeight: 15, marginTop: 6, maxWidth: 235, textAlign: "center" }, graphic: { alignItems: "center", alignSelf: "center", borderColor: "#DCEBFC", borderRadius: 73, borderWidth: 5, height: 146, justifyContent: "center", marginTop: 27, width: 146 }, faceGraphic: { backgroundColor: "rgba(230,244,255,0.7)", borderWidth: 0, height: 135, position: "relative", width: 135 }, facePerson: { position: "absolute" }, button: { alignItems: "center", backgroundColor: "#0874F9", borderRadius: 25, elevation: 8, marginTop: 28, paddingVertical: 14, shadowColor: "#0874F9", shadowOffset: { width: 0, height: 7 }, shadowOpacity: 0.27, shadowRadius: 10 }, buttonText: { color: "#FFF", fontSize: 11, fontWeight: "700" }, skip: { alignItems: "center", paddingVertical: 14 }, skipText: { color: "#60718C", fontSize: 10, fontWeight: "600" } });
