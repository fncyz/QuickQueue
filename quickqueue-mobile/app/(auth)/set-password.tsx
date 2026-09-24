import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import SecuritySetupProgress from "@/components/SecuritySetupProgress";
import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";
import SecurityGradientButton from "@/components/SecurityGradientButton";
import { Text, TextInput } from "@/components/Typography";
import { setInitialPassword } from "@/services/api";

const passwordChecks = (value: string) => [
  { label: "At least 8 characters", valid: value.length >= 8 },
  { label: "One uppercase and one lowercase letter", valid: /[A-Z]/.test(value) && /[a-z]/.test(value) },
  { label: "One number", valid: /\d/.test(value) },
  { label: "One special character", valid: /[^A-Za-z0-9]/.test(value) },
];

export default function SetPasswordScreen() {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [saving, setSaving] = useState(false);
  const checks = passwordChecks(password);
  const valid = checks.every((item) => item.valid) && password === confirmation && confirmation.length > 0;

  const submit = async () => {
    if (!valid || saving) return;
    try {
      setSaving(true);
      const token = await AsyncStorage.getItem("quickqueue.accessToken");
      if (!token) return router.replace("/login");
      await setInitialPassword(token, password, confirmation);
      await AsyncStorage.setItem("quickqueue.securitySetupStage", "pin");
      router.replace("/set-pin");
    } catch (error: any) {
      Alert.alert("Password not saved", error?.response?.data?.message || "Please try again.");
    } finally { setSaving(false); }
  };

  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}><SecuritySetupBackdrop /><KeyboardAvoidingView style={s.keyboard} behavior={Platform.OS === "ios" ? "padding" : undefined}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
    <SecuritySetupProgress current={1} />
    <View style={s.icon}><Ionicons name="shield" size={34} color="#0645A8" /><Ionicons name="lock-closed" size={11} color="#FFF" style={s.lockOverlay} /></View>
    <Text style={s.title}>Create Password</Text>
    <Text style={s.description}>Create a strong password to protect your QuickQueue account.</Text>
    <PasswordField label="Create Password" placeholder="Enter your password" value={password} onChangeText={setPassword} visible={showPassword} onToggle={() => setShowPassword((value) => !value)} />
    <PasswordField label="Confirm Password" placeholder="Re-enter your password" value={confirmation} onChangeText={setConfirmation} visible={showConfirmation} onToggle={() => setShowConfirmation((value) => !value)} />
    {confirmation.length > 0 && password !== confirmation && <Text style={s.error}>Passwords do not match.</Text>}
    <View style={s.rules}><Text style={s.rulesTitle}>Your password must include:</Text>{checks.map((item) => <View key={item.label} style={s.ruleRow}><Ionicons name={item.valid ? "checkmark-circle" : "ellipse-outline"} size={15} color={item.valid ? "#1DAA61" : "#94A0B4"} /><Text style={[s.rule, item.valid && s.ruleValid]}>{item.label}</Text></View>)}</View>
    <SecurityGradientButton onPress={submit} disabled={!valid || saving} label={saving ? "Creating Password..." : "Create Password"} style={s.button} />
  </ScrollView></KeyboardAvoidingView></SafeAreaView>;
}

function PasswordField({ label, placeholder, value, onChangeText, visible, onToggle }: { label: string; placeholder: string; value: string; onChangeText: (value: string) => void; visible: boolean; onToggle: () => void }) {
  return <View style={s.field}><Text style={s.label}>{label}</Text><View style={s.inputShell}><Ionicons name="lock-closed-outline" size={20} color="#0759D9" /><TextInput style={s.input} value={value} onChangeText={onChangeText} secureTextEntry={!visible} autoCapitalize="none" autoCorrect={false} placeholder={placeholder} placeholderTextColor="#8A94A8" /><Pressable onPress={onToggle} style={s.eye} accessibilityLabel={visible ? "Hide password" : "Show password"}><Ionicons name={visible ? "eye-outline" : "eye-off-outline"} size={22} color="#0759D9" /></Pressable></View></View>;
}

const s = StyleSheet.create({
  safe: { backgroundColor: "#F8FBFF", flex: 1 }, keyboard: { flex: 1 }, content: { flexGrow: 1, paddingHorizontal: 22, paddingBottom: 25, paddingTop: 45 },
  icon: { alignItems: "center", alignSelf: "center", backgroundColor: "#EEF5FF", borderRadius: 32, height: 64, justifyContent: "center", marginTop: 2, position: "relative", width: 64 }, lockOverlay: { position: "absolute", top: 27 }, title: { color: "#082A72", fontSize: 24, fontWeight: "800", marginTop: 17, textAlign: "center" }, description: { color: "#7083A2", fontSize: 12, lineHeight: 18, marginBottom: 10, marginTop: 4, textAlign: "center" },
  field: { marginTop: 10 }, label: { color: "#233F73", fontSize: 12, fontWeight: "600", marginBottom: 5 }, inputShell: { alignItems: "center", backgroundColor: "rgba(255,255,255,0.82)", borderColor: "#AFC9EF", borderRadius: 8, borderWidth: 1, flexDirection: "row", height: 49, paddingLeft: 13 }, input: { color: "#18233C", flex: 1, fontSize: 13, height: "100%", paddingHorizontal: 11 }, eye: { alignItems: "center", height: "100%", justifyContent: "center", paddingHorizontal: 13 },
  error: { color: "#D62F45", fontSize: 10, marginTop: 5 }, rules: { backgroundColor: "transparent", marginTop: 10, paddingHorizontal: 4 }, rulesTitle: { color: "#46658F", fontSize: 11, fontWeight: "700", marginBottom: 4 }, ruleRow: { alignItems: "center", flexDirection: "row", gap: 6, marginVertical: 1 }, rule: { color: "#7183A0", fontSize: 10 }, ruleValid: { color: "#16864E" },
  button: { marginTop: 22 },
});
