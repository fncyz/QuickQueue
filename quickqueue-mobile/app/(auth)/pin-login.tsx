import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";
import SecurityGradientButton from "@/components/SecurityGradientButton";
import { Text } from "@/components/Typography";
import { loginResidentWithPin } from "@/services/api";

const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "back"];
const letters: Record<string, string> = { "2": "ABC", "3": "DEF", "4": "GHI", "5": "JKL", "6": "MNO", "7": "PQRS", "8": "TUV", "9": "WXYZ" };

export default function PinLoginScreen() {
  const { username = "" } = useLocalSearchParams<{ username?: string }>();
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const pressKey = (key: string) => {
    setError("");
    if (key === "back") return setPin((value) => value.slice(0, -1));
    if (key && pin.length < 4) setPin((value) => `${value}${key}`);
  };

  const submit = async () => {
    if (pin.length !== 4 || submitting) return;
    try {
      setSubmitting(true);
      setError("");
      const result = await loginResidentWithPin(username.trim(), pin);
      await AsyncStorage.multiSet([
        ["quickqueue.accessToken", result.access],
        ["quickqueue.refreshToken", result.refresh],
        ["quickqueue.securitySetupStage", result.security_setup_stage],
      ]);
      router.replace("/(tabs)");
    } catch (requestError: any) {
      setPin("");
      setError(requestError?.response?.data?.message || "PIN sign in could not be completed.");
    } finally {
      setSubmitting(false);
    }
  };

  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}>
    <SecuritySetupBackdrop />
    <View style={s.content}>
      <Pressable onPress={() => router.back()} style={s.back} accessibilityLabel="Back to sign in"><Ionicons name="chevron-back" size={25} color="#083778" /></Pressable>
      <View style={s.iconHalo}><View style={s.icon}><Ionicons name="shield-checkmark" size={31} color="#FFF" /></View></View>
      <Text style={s.title}>Enter Your Secure PIN</Text>
      <Text style={s.description}>Sign in as {username} using your 4-digit PIN.</Text>
      <View style={s.pinRow}>{[0, 1, 2, 3].map((index) => <View key={index} style={[s.pinBox, pin.length === index && s.pinBoxActive]}>{index < pin.length && <View style={s.dot} />}</View>)}</View>
      {!!error && <Text style={s.error}>{error}</Text>}
      <SecurityGradientButton onPress={submit} disabled={pin.length !== 4 || submitting} label={submitting ? "Signing In..." : "Sign In"} style={s.button} />
      <View style={s.keypad}>{keys.map((key, index) => key === "" ? <View key={`spacer-${index}`} style={s.key} /> : <Pressable key={`key-${key}`} onPress={() => pressKey(key)} style={s.key}>{key === "back" ? <Ionicons name="backspace-outline" size={22} color="#113878" /> : <><Text style={s.keyNumber}>{key}</Text>{letters[key] && <Text style={s.keyLetters}>{letters[key]}</Text>}</>}</Pressable>)}</View>
    </View>
  </SafeAreaView>;
}

const s = StyleSheet.create({
  safe: { backgroundColor: "#F8FBFF", flex: 1 }, content: { flex: 1, paddingHorizontal: 24, paddingTop: 22 }, back: { alignItems: "center", height: 44, justifyContent: "center", width: 44 },
  iconHalo: { alignItems: "center", alignSelf: "center", backgroundColor: "rgba(224,239,255,0.72)", borderRadius: 38, height: 76, justifyContent: "center", marginTop: 18, width: 76 },
  icon: { alignItems: "center", backgroundColor: "#0645A8", borderRadius: 25, height: 50, justifyContent: "center", width: 50 },
  title: { color: "#082A72", fontSize: 24, fontWeight: "800", marginTop: 17, textAlign: "center" }, description: { color: "#7083A2", fontSize: 12, marginTop: 5, textAlign: "center" },
  pinRow: { flexDirection: "row", gap: 8, justifyContent: "center", marginTop: 30 }, pinBox: { alignItems: "center", backgroundColor: "#FFF", borderColor: "#D6E0EF", borderRadius: 10, borderWidth: 1, height: 52, justifyContent: "center", width: 54 }, pinBoxActive: { borderColor: "#1671FF" }, dot: { backgroundColor: "#153A76", borderRadius: 6, height: 12, width: 12 },
  error: { color: "#B42318", fontSize: 11, marginTop: 12, textAlign: "center" }, button: { marginTop: 25 },
  keypad: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", marginTop: 24 }, key: { alignItems: "center", backgroundColor: "rgba(255,255,255,0.82)", borderColor: "#E7EEF8", borderRadius: 9, borderWidth: 1, height: 56, justifyContent: "center", margin: 4, width: "29%" }, keyNumber: { color: "#0B2E70", fontSize: 18, fontWeight: "700", lineHeight: 21 }, keyLetters: { color: "#6F80A0", fontSize: 6, letterSpacing: 2 },
});
