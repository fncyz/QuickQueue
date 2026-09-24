import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { Alert, Pressable, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";
import SecuritySetupProgress from "@/components/SecuritySetupProgress";
import SecurityGradientButton from "@/components/SecurityGradientButton";
import { Text } from "@/components/Typography";
import { setSecurityPin } from "@/services/api";

const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "back"];
const letters: Record<string, string> = { "2": "ABC", "3": "DEF", "4": "GHI", "5": "JKL", "6": "MNO", "7": "PQRS", "8": "TUV", "9": "WXYZ" };

export default function SetPinScreen() {
  const [pin, setPin] = useState("");
  const [saving, setSaving] = useState(false);
  const pressKey = (key: string) => {
    if (key === "back") return setPin((value) => value.slice(0, -1));
    if (key && pin.length < 4) setPin((value) => `${value}${key}`);
  };
  const submit = async () => {
    if (pin.length !== 4 || saving) return;
    try {
      setSaving(true);
      const token = await AsyncStorage.getItem("quickqueue.accessToken");
      if (!token) return router.replace("/login");
      await setSecurityPin(token, pin);
      setPin("");
      await AsyncStorage.setItem("quickqueue.securitySetupStage", "fingerprint");
      router.replace("/setup-fingerprint");
    } catch (error: any) { Alert.alert("PIN not saved", error?.response?.data?.message || "Please try again."); }
    finally { setSaving(false); }
  };
  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}><SecuritySetupBackdrop /><View style={s.content}>
    <SecuritySetupProgress current={2} />
    <View style={s.icon}><Ionicons name="shield-checkmark" size={30} color="#FFF" /></View>
    <Text style={s.title}>Set Your Secure PIN</Text>
    <Text style={s.description}>Add a 4 digit PIN to protect your account and for quick access.</Text>
    <View style={s.pinRow}>{[0, 1, 2, 3].map((index) => <View key={index} style={[s.pinBox, pin.length === index && s.pinBoxActive]}>{index < pin.length && <View style={s.dot} />}</View>)}</View>
    <SecurityGradientButton onPress={submit} disabled={pin.length !== 4 || saving} label={saving ? "Saving Passkey..." : "Set Passkey"} style={s.button} />
    <View style={s.keypad}>{keys.map((key, index) => key === "" ? <View key={`spacer-${index}`} style={s.key} /> : <Pressable key={`key-${key}`} onPress={() => pressKey(key)} style={s.key}>{key === "back" ? <Ionicons name="backspace-outline" size={21} color="#113878" /> : <><Text style={s.keyNumber}>{key}</Text>{letters[key] && <Text style={s.keyLetters}>{letters[key]}</Text>}</>}</Pressable>)}</View>
  </View></SafeAreaView>;
}

const s = StyleSheet.create({
  safe: { backgroundColor: "#F8FBFF", flex: 1 }, content: { flex: 1, paddingHorizontal: 22, paddingTop: 45 },
  icon: { alignItems: "center", alignSelf: "center", backgroundColor: "#0645A8", borderRadius: 32, height: 64, justifyContent: "center", marginTop: 2, width: 64 },
  title: { color: "#082A72", fontSize: 24, fontWeight: "800", marginTop: 17, textAlign: "center" }, description: { color: "#7083A2", fontSize: 12, lineHeight: 18, marginTop: 4, textAlign: "center" },
  pinRow: { flexDirection: "row", gap: 7, justifyContent: "center", marginTop: 24 }, pinBox: { alignItems: "center", backgroundColor: "#FFF", borderColor: "#D6E0EF", borderRadius: 10, borderWidth: 1, height: 49, justifyContent: "center", width: 51 }, pinBoxActive: { borderColor: "#1671FF" }, dot: { backgroundColor: "#153A76", borderRadius: 6, height: 12, width: 12 },
  button: { marginTop: 27 },
  keypad: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", marginHorizontal: -3, marginTop: 24 }, key: { alignItems: "center", backgroundColor: "rgba(255,255,255,0.78)", borderColor: "#ECF1F8", borderRadius: 8, borderWidth: 1, height: 53, justifyContent: "center", margin: 3, width: "30%" }, keyNumber: { color: "#0B2E70", fontSize: 17, fontWeight: "700", lineHeight: 20 }, keyLetters: { color: "#6F80A0", fontSize: 6, letterSpacing: 2 },
});
