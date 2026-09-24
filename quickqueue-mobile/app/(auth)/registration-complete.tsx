import AsyncStorage from "@react-native-async-storage/async-storage";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Text } from "@/components/Typography";
import SecuritySetupBackdrop from "@/components/SecuritySetupBackdrop";

export default function RegistrationCompleteScreen() {
  const [username, setUsername] = useState("");
  useEffect(() => { AsyncStorage.getItem("quickqueue.pendingUsername").then((value) => setUsername(value || "")); }, []);
  const backToSignIn = async () => {
    await AsyncStorage.multiRemove(["quickqueue.accessToken", "quickqueue.refreshToken", "quickqueue.securitySetupStage", "quickqueue.pendingUsername", "quickqueue.requiresInitialPassword"]);
    router.replace({ pathname: "/login", params: username ? { username } : {} });
  };
  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}><SecuritySetupBackdrop /><View style={s.content}><View style={s.iconHalo}><View style={s.icon}><Ionicons name="checkmark" size={49} color="#FFF" /></View></View><Text style={s.title}>Congratulations!</Text><Text style={s.description}>You are all set! Your account has successfully registered.</Text><Pressable onPress={backToSignIn} style={s.button}><Text style={s.buttonText}>Back to Sign In</Text></Pressable></View></SafeAreaView>;
}
const s = StyleSheet.create({ safe: { backgroundColor: "#F8FBFF", flex: 1 }, content: { alignItems: "center", flex: 1, paddingHorizontal: 30, paddingTop: 145 }, iconHalo: { alignItems: "center", backgroundColor: "rgba(63,156,255,0.18)", borderRadius: 57, height: 114, justifyContent: "center", width: 114 }, icon: { alignItems: "center", backgroundColor: "#1680FF", borderColor: "#6CB5FF", borderRadius: 41, borderWidth: 7, height: 82, justifyContent: "center", shadowColor: "#1680FF", shadowOffset: { width: 0, height: 7 }, shadowOpacity: 0.3, shadowRadius: 12, width: 82 }, title: { color: "#082A72", fontSize: 24, fontWeight: "800", marginTop: 27 }, description: { color: "#7083A2", fontSize: 10, lineHeight: 16, marginTop: 8, maxWidth: 235, textAlign: "center" }, button: { alignItems: "center", alignSelf: "stretch", backgroundColor: "#0874F9", borderRadius: 25, elevation: 8, marginTop: 52, paddingVertical: 14, shadowColor: "#0874F9", shadowOffset: { width: 0, height: 7 }, shadowOpacity: 0.27, shadowRadius: 10 }, buttonText: { color: "#FFF", fontSize: 11, fontWeight: "700" } });
