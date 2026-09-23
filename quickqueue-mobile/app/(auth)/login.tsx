import { useState } from "react";
import {
  Image,
  ImageBackground,
  KeyboardAvoidingView,
  Dimensions,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Text, TextInput } from '@/components/Typography';
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { loginResident } from "@/services/api";

const loginBackground = require("../../assets/images/login.png");
const quickQueueLogo = require("../../assets/images/logo.png");
const screenSize = Dimensions.get("screen");

export default function LoginScreen() {
  const router = useRouter();
  const { created, username: createdUsername, temporaryPassword } = useLocalSearchParams<{
    created?: string;
    username?: string;
    temporaryPassword?: string;
  }>();
  const accountWasCreated = created === "true" && !!temporaryPassword;
  const [username, setUsername] = useState(createdUsername ?? "");
  const [password, setPassword] = useState(temporaryPassword ?? "");
  const [isPasswordVisible, setPasswordVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");

  const copyTemporaryPassword = async () => {
    if (!temporaryPassword) return;

    // Browser builds support the standard clipboard API. Native clipboard support
    // can be enabled later with expo-clipboard when package downloads are available.
    if (Platform.OS === "web" && typeof navigator !== "undefined" && navigator.clipboard) {
      await navigator.clipboard.writeText(temporaryPassword);
      setCopyStatus("Password copied!");
    } else {
      setPassword(temporaryPassword);
      setCopyStatus("Password added to the sign-in field below.");
    }
  };

  const handleLogin = async () => {
    const normalizedUsername = username.trim();

    if (!normalizedUsername || !password) {
      setLoginError("Enter your username and password.");
      return;
    }
    setIsSubmitting(true);
    setLoginError("");

    let result;
    try {
      result = await loginResident(normalizedUsername, password);
    } catch (error: any) {
      if (error?.response?.status === 401) {
        setLoginError("Invalid username or password. Please try again.");
      } else if (!error?.response) {
        setLoginError("Cannot reach the QuickQueue server. Make sure your phone and computer are on the same Wi-Fi.");
      } else {
        setLoginError(error.response.data?.message || "The QuickQueue server could not complete the login.");
      }
      setIsSubmitting(false);
      return;
    }

    try {
      await AsyncStorage.setItem("quickqueue.accessToken", result.access);
      await AsyncStorage.setItem("quickqueue.refreshToken", result.refresh);
      if (accountWasCreated) {
        await AsyncStorage.setItem("quickqueue.requiresInitialPassword", "true");
      }
    } catch {
      setIsSubmitting(false);
      setLoginError("Login succeeded, but the app could not save your session. Restart the app and try again.");
      return;
    }

    setIsSubmitting(false);
    router.replace(accountWasCreated ? "/set-password" : "/(tabs)");
  };

  return (
    <View style={styles.container}>
      <ImageBackground
        source={loginBackground}
        resizeMode="cover"
        style={styles.fixedBackground}
      >
        <View />
      </ImageBackground>
      <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
        <KeyboardAvoidingView
          style={styles.keyboardView}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.branding}>
              <View style={styles.logoFrame}>
                <Image source={quickQueueLogo} style={styles.logo} accessibilityLabel="QuickQueue logo" />
              </View>
              <Text style={styles.welcome}>WELCOME!</Text>
              <Text style={styles.subtitle}>Sign in to your QuickQueue account</Text>
            </View>

            <View style={[styles.form, accountWasCreated && styles.formAfterNotice]}>
              {accountWasCreated && (
                <View style={styles.accountCreatedNotice} accessibilityRole="alert">
                  <View style={styles.noticeHeading}>
                    <Ionicons name="checkmark-circle" size={27} color="#18C36B" />
                    <View style={styles.noticeHeadingText}>
                      <Text style={styles.noticeTitle}>Account Created Successfully!</Text>
                      <Text style={styles.noticeDescription}>Your username has been filled automatically. Copy your password below to sign in.</Text>
                    </View>
                  </View>
                  <View style={styles.passwordCopyRow}>
                    <Text style={styles.passwordLabel}>Password:</Text>
                    <Text selectable style={styles.temporaryPassword} accessibilityLabel="Temporary password. Tap and hold to copy.">
                      {temporaryPassword}
                    </Text>
                    <Pressable onPress={copyTemporaryPassword} style={styles.copyButton} accessibilityRole="button" accessibilityLabel="Copy temporary password">
                      <Ionicons name="copy-outline" size={15} color="#003D9C" />
                      <Text style={styles.copyButtonText}>Copy</Text>
                    </Pressable>
                  </View>
                  <Text style={styles.copyHint}>{copyStatus || "Tap Copy to use this password for sign in."}</Text>
                </View>
              )}

              {!!loginError && <Text style={styles.loginError}>{loginError}</Text>}

              {accountWasCreated && (
                <View style={styles.securityNotice}>
                  <Ionicons name="warning" size={23} color="#FFC21C" />
                  <Text style={styles.securityNoticeText}>Please screenshot or copy your account details. For your security, this password will not be shown again.</Text>
                </View>
              )}

              <Text style={styles.label}>Username</Text>
              <View style={styles.inputShell}>
                <View style={styles.inputIcon}>
                  <Ionicons name="person-outline" size={23} color="#0045AA" />
                </View>
                <TextInput
                  placeholder="Enter your username"
                  placeholderTextColor="#7C8499"
                  value={username}
                  onChangeText={setUsername}
                  style={styles.input}
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="next"
                />
              </View>

              <Text style={styles.label}>Password</Text>
              <View style={styles.inputShell}>
                <View style={styles.inputIcon}>
                  <Ionicons name="lock-closed-outline" size={22} color="#0045AA" />
                </View>
                <TextInput
                  placeholder="Enter your password"
                  placeholderTextColor="#7C8499"
                  value={password}
                  onChangeText={setPassword}
                  style={styles.input}
                  secureTextEntry={!isPasswordVisible}
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="done"
                  onSubmitEditing={handleLogin}
                />
                <Pressable
                  onPress={() => setPasswordVisible((visible) => !visible)}
                  style={styles.eyeButton}
                  accessibilityRole="button"
                  accessibilityLabel={isPasswordVisible ? "Hide password" : "Show password"}
                >
                  <Ionicons name={isPasswordVisible ? "eye-off-outline" : "eye-outline"} size={24} color="#0045AA" />
                </Pressable>
              </View>

              <Pressable style={styles.forgotPassword} accessibilityRole="button">
                <Text style={styles.forgotPasswordText}>Forgot Password?</Text>
              </Pressable>

              <Pressable style={[styles.signInButton, isSubmitting && styles.signInButtonDisabled]} onPress={handleLogin} disabled={isSubmitting} accessibilityRole="button">
                <Text style={styles.signInText}>{isSubmitting ? "Signing In..." : "Sign In"}</Text>
              </Pressable>

              <View style={styles.signupRow}>
                <Text style={styles.signupText}>Don’t have an account? </Text>
                <Pressable onPress={() => router.push("/register")} accessibilityRole="link">
                  <Text style={styles.signupLink}>Sign Up</Text>
                </Pressable>
              </View>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#003D9C", overflow: "hidden" },
  fixedBackground: { height: screenSize.height, left: 0, position: "absolute", top: 0, width: screenSize.width },
  safeArea: { flex: 1 },
  keyboardView: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingHorizontal: 42, paddingBottom: 26 },
  branding: { alignItems: "center", paddingTop: 34 },
  logoFrame: {
    alignItems: "center",
    backgroundColor: "#FFC21C",
    borderRadius: 67,
    height: 134,
    justifyContent: "center",
    marginBottom: 14,
    width: 134,
  },
  logo: { width: 122, height: 122, borderRadius: 61 },
  welcome: { color: "#002C7C", fontSize: 31, fontWeight: "800", letterSpacing: -0.8 },
  subtitle: { color: "#62697B", fontSize: 14, marginTop: 4, textAlign: "center" },
  form: { marginTop: 69 },
  formAfterNotice: { marginTop: 26 },
  accountCreatedNotice: { backgroundColor: "rgba(30, 92, 180, 0.72)", borderColor: "#8EB4ED", borderRadius: 11, borderWidth: 1, marginBottom: 11, padding: 13 },
  noticeHeading: { alignItems: "flex-start", flexDirection: "row", gap: 10 },
  noticeHeadingText: { flex: 1 },
  noticeTitle: { color: "#FFFFFF", fontSize: 14, fontWeight: "800" },
  noticeDescription: { color: "#EAF2FF", fontSize: 11, lineHeight: 16, marginTop: 2 },
  passwordCopyRow: { alignItems: "center", flexDirection: "row", marginTop: 9 },
  passwordLabel: { color: "#FFFFFF", fontSize: 12, fontWeight: "700", marginRight: 5 },
  temporaryPassword: { color: "#72EBAE", fontSize: 14, fontWeight: "800", letterSpacing: 0.5, marginRight: 6 },
  copyButton: { alignItems: "center", backgroundColor: "#FFFFFF", borderRadius: 5, flexDirection: "row", gap: 3, marginLeft: "auto", paddingHorizontal: 8, paddingVertical: 5 },
  copyButtonText: { color: "#003D9C", fontSize: 10, fontWeight: "800" },
  copyHint: { color: "#D9E7FC", fontSize: 10, marginTop: 6 },
  securityNotice: { alignItems: "center", backgroundColor: "rgba(30, 92, 180, 0.72)", borderColor: "#8EB4ED", borderRadius: 11, borderWidth: 1, flexDirection: "row", gap: 11, marginBottom: 12, padding: 12 },
  securityNoticeText: { color: "#FFFFFF", flex: 1, fontSize: 10, lineHeight: 14 },
  label: { color: "#FFFFFF", fontSize: 14, fontWeight: "700", marginBottom: 8 },
  inputShell: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 11,
    elevation: 5,
    flexDirection: "row",
    height: 61,
    marginBottom: 22,
    shadowColor: "#001B51",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.23,
    shadowRadius: 7,
  },
  inputIcon: { alignItems: "center", backgroundColor: "#F0F4FF", borderRadius: 10, height: 44, justifyContent: "center", marginLeft: 8, width: 42 },
  input: { color: "#18233C", flex: 1, fontSize: 14, height: "100%", paddingHorizontal: 13 },
  eyeButton: { alignItems: "center", height: "100%", justifyContent: "center", paddingHorizontal: 14 },
  forgotPassword: { alignSelf: "flex-end", marginTop: -9, paddingVertical: 5 },
  forgotPasswordText: { color: "#1FB7EE", fontSize: 13 },
  signInButton: {
    alignItems: "center",
    backgroundColor: "#FFC21C",
    borderRadius: 11,
    elevation: 4,
    justifyContent: "center",
    height: 56,
    marginTop: 22,
    shadowColor: "#001B51",
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
  },
  signInText: { color: "#002C7C", fontSize: 18, fontWeight: "800" },
  signInButtonDisabled: { opacity: 0.7 },
  loginError: { color: "#FFD1D1", fontSize: 12, fontWeight: "600", marginBottom: 8, textAlign: "center" },
  signupRow: { alignItems: "center", flexDirection: "row", justifyContent: "center", marginTop: 22 },
  signupText: { color: "#FFFFFF", fontSize: 14 },
  signupLink: { color: "#FFC21C", fontSize: 14, fontWeight: "600" },
});
