import AsyncStorage from "@react-native-async-storage/async-storage";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, StyleSheet } from "react-native";
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
  return <SafeAreaView style={s.safe} edges={["top", "bottom"]}>
    <SecuritySetupBackdrop />
    <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
      <SuccessAnimation color="#1680FF" size={112} />
      <Text style={s.title}>Congratulations!</Text>
      <Text style={s.description}>You are all set! Your account has been{`\n`}successfully registered.</Text>
      <SecurityGradientButton onPress={backToSignIn} label="Back to Sign In" style={s.button} />
    </ScrollView>
  </SafeAreaView>;
}
const s = StyleSheet.create({
  safe: { backgroundColor: "#F8FBFF", flex: 1 },
  content: { alignItems: "center", alignSelf: "center", flexGrow: 1, justifyContent: "center", maxWidth: 500, paddingBottom: 32, paddingHorizontal: 26, paddingTop: 32, width: "100%" },
  title: { color: "#082A72", fontSize: 28, fontWeight: "800", letterSpacing: -0.6, marginTop: 22, textAlign: "center" },
  description: { color: "#7083A2", fontSize: 14, lineHeight: 21, marginTop: 13, maxWidth: 300, textAlign: "center" },
  button: { alignSelf: "stretch", marginTop: 48 },
});
