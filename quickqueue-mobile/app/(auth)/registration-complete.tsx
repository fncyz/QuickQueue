import AsyncStorage from "@react-native-async-storage/async-storage";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Text } from "@/components/Typography";
import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";
import SecurityGradientButton from "@/components/SecurityGradientButton";
import { SuccessAnimation } from "@/components/SuccessAnimation";

export default function RegistrationCompleteScreen() {
  const [username, setUsername] = useState("");
  useEffect(() => { AsyncStorage.getItem("quickqueue.pendingUsername").then((value) => setUsername(value || "")); }, []);
  const backToSignIn = async () => {
    await AsyncStorage.multiRemove(["quickqueue.accessToken", "quickqueue.refreshToken", "quickqueue.securitySetupStage", "quickqueue.pendingUsername", "quickqueue.requiresInitialPassword"]);
    router.replace({ pathname: "/login", params: username ? { username } : {} });
  };
  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}><SecuritySetupBackdrop /><View style={s.content}><SuccessAnimation color="#1680FF" size={114} /><Text style={s.title}>Account Created Successfully!</Text><Text style={s.description}>You are all set. Your QuickQueue account is ready to use.</Text><SecurityGradientButton onPress={backToSignIn} label="Back to Sign In" style={s.button} /></View></SafeAreaView>;
}
const s = StyleSheet.create({ safe: { backgroundColor: "#F8FBFF", flex: 1 }, content: { alignItems: "center", flex: 1, paddingHorizontal: 30, paddingTop: 145 }, iconHalo: { alignItems: "center", backgroundColor: "rgba(63,156,255,0.18)", borderRadius: 57, height: 114, justifyContent: "center", width: 114 }, icon: { alignItems: "center", backgroundColor: "#1680FF", borderColor: "#6CB5FF", borderRadius: 41, borderWidth: 7, height: 82, justifyContent: "center", shadowColor: "#1680FF", shadowOffset: { width: 0, height: 7 }, shadowOpacity: 0.3, shadowRadius: 12, width: 82 }, title: { color: "#082A72", fontSize: 24, fontWeight: "800", marginTop: 27 }, description: { color: "#7083A2", fontSize: 12, lineHeight: 18, marginTop: 8, maxWidth: 265, textAlign: "center" }, button: { alignSelf: "stretch", marginTop: 52 } });
