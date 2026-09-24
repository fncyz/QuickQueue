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
import * as LocalAuthentication from "expo-local-authentication";
import { loginResident, refreshResidentSession } from "@/services/api";
import { getBiometricLogin, updateBiometricRefreshToken, type BiometricKind } from "@/services/secure-auth";

const setupRoute = (stage: string) => {
  if (stage === "password") return "/set-password" as const;
  if (stage === "pin") return "/set-pin" as const;
  if (stage === "fingerprint") return "/setup-fingerprint" as const;
  if (stage === "face") return "/setup-face" as const;
  return "/(tabs)" as const;
};

const loginBackground = require("../../assets/images/login.png");
const quickQueueLogo = require("../../assets/images/logo.png");
const screenSize = Dimensions.get("screen");

export default function LoginScreen() {
  const router = useRouter();
  const { username: createdUsername } = useLocalSearchParams<{
    username?: string;
  }>();
  const [username, setUsername] = useState(createdUsername ?? "");
  const [password, setPassword] = useState("");
  const [isPasswordVisible, setPasswordVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");

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
      await AsyncStorage.setItem("quickqueue.securitySetupStage", result.security_setup_stage);
      await updateBiometricRefreshToken(result.refresh);
    } catch {
      setIsSubmitting(false);
      setLoginError("Login succeeded, but the app could not save your session. Restart the app and try again.");
      return;
    }

    setIsSubmitting(false);
    router.replace(setupRoute(result.security_setup_stage));
  };

  const handlePinLogin = () => {
    const normalizedUsername = username.trim();
    if (!normalizedUsername) {
      setLoginError("Enter your username before using your PIN.");
      return;
    }
    setLoginError("");
    router.push({ pathname: "/pin-login", params: { username: normalizedUsername } });
  };

  const handleBiometricLogin = async (kind: BiometricKind) => {
    if (isSubmitting) return;
    try {
      setIsSubmitting(true);
      setLoginError("");
      const requestedType = kind === "fingerprint"
        ? LocalAuthentication.AuthenticationType.FINGERPRINT
        : LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION;
      const [hardware, enrolled, supportedTypes, savedLogin] = await Promise.all([
        LocalAuthentication.hasHardwareAsync(),
        LocalAuthentication.isEnrolledAsync(),
        LocalAuthentication.supportedAuthenticationTypesAsync(),
        getBiometricLogin(kind),
      ]);
      if (!hardware || !enrolled || !supportedTypes.includes(requestedType)) {
        setLoginError(`${kind === "fingerprint" ? "Fingerprint" : "Face recognition"} is not available on this device.`);
        return;
      }
      if (!savedLogin.enabled || !savedLogin.refreshToken) {
        setLoginError(`Sign in with your password first and enable ${kind === "fingerprint" ? "fingerprint" : "face recognition"} during security setup.`);
        return;
      }
      const authentication = await LocalAuthentication.authenticateAsync({
        promptMessage: kind === "fingerprint" ? "Sign in with fingerprint" : "Sign in with face recognition",
        cancelLabel: "Cancel",
        disableDeviceFallback: true,
      });
      if (!authentication.success) return;
      const session = await refreshResidentSession(savedLogin.refreshToken);
      const refreshToken = session.refresh || savedLogin.refreshToken;
      await AsyncStorage.multiSet([
        ["quickqueue.accessToken", session.access],
        ["quickqueue.refreshToken", refreshToken],
        ["quickqueue.securitySetupStage", "complete"],
      ]);
      await updateBiometricRefreshToken(refreshToken);
      router.replace("/(tabs)");
    } catch (error: any) {
      if (error?.response?.status === 401) {
        setLoginError("Your saved sign-in expired. Sign in with your password to enable it again.");
      } else {
        setLoginError("Biometric sign in could not be completed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
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
              <Text style={styles.welcome}>WELCOME</Text>
              <Text style={styles.subtitle}>Sign in to your QuickQueue account</Text>
            </View>

            <View style={styles.form}>

              {!!loginError && <Text style={styles.loginError}>{loginError}</Text>}

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
                  <Ionicons name={isPasswordVisible ? "eye-outline" : "eye-off-outline"} size={24} color="#0045AA" />
                </Pressable>
              </View>

              <Pressable style={[styles.signInButton, isSubmitting && styles.signInButtonDisabled]} onPress={handleLogin} disabled={isSubmitting} accessibilityRole="button">
                <Text style={styles.signInText}>{isSubmitting ? "Signing In..." : "Sign In"}</Text>
              </Pressable>

              <View style={styles.continueRow}>
                <View style={styles.divider} />
                <Text style={styles.continueText}>Or continue with</Text>
                <View style={styles.divider} />
              </View>

              <View style={styles.alternativeRow}>
                <Pressable onPress={handlePinLogin} disabled={isSubmitting} style={styles.alternativeButton} accessibilityRole="button" accessibilityLabel="Sign in with secure PIN">
                  <Ionicons name="key" size={27} color="#003D9C" />
                </Pressable>
                <Pressable onPress={() => handleBiometricLogin("fingerprint")} disabled={isSubmitting} style={styles.alternativeButton} accessibilityRole="button" accessibilityLabel="Sign in with fingerprint">
                  <Ionicons name="finger-print" size={31} color="#003D9C" />
                </Pressable>
                <Pressable onPress={() => handleBiometricLogin("face")} disabled={isSubmitting} style={styles.alternativeButton} accessibilityRole="button" accessibilityLabel="Sign in with face recognition">
                  <View style={styles.faceScanner}>
                    <View style={[styles.scanCorner, styles.scanTopLeft]} />
                    <View style={[styles.scanCorner, styles.scanTopRight]} />
                    <View style={[styles.scanCorner, styles.scanBottomLeft]} />
                    <View style={[styles.scanCorner, styles.scanBottomRight]} />
                    <View style={[styles.faceEye, styles.faceLeftEye]} />
                    <View style={[styles.faceEye, styles.faceRightEye]} />
                    <View style={styles.faceSmile} />
                  </View>
                </Pressable>
              </View>

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
  scrollContent: { flexGrow: 1, paddingHorizontal: 36, paddingBottom: 24 },
  branding: { alignItems: "center", paddingTop: 34 },
  logoFrame: {
    alignItems: "center",
    backgroundColor: "#063F96",
    borderRadius: 55,
    height: 110,
    justifyContent: "center",
    marginBottom: 9,
    overflow: "hidden",
    width: 110,
  },
  logo: { height: 130, resizeMode: "stretch", width: 160 },
  welcome: { color: "#002C7C", fontSize: 31, fontWeight: "800", letterSpacing: -0.8, lineHeight: 38 },
  subtitle: { color: "#62697B", fontSize: 14, marginTop: 4, textAlign: "center" },
  form: { marginTop: 58 },
  label: { color: "#FFFFFF", fontSize: 13, fontWeight: "700", marginBottom: 7 },
  inputShell: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 11,
    elevation: 5,
    flexDirection: "row",
    height: 56,
    marginBottom: 18,
    shadowColor: "#001B51",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.23,
    shadowRadius: 7,
  },
  inputIcon: { alignItems: "center", backgroundColor: "#F0F4FF", borderRadius: 9, height: 42, justifyContent: "center", marginLeft: 7, width: 37 },
  input: { color: "#18233C", flex: 1, fontSize: 13, height: "100%", paddingHorizontal: 13 },
  eyeButton: { alignItems: "center", height: "100%", justifyContent: "center", paddingHorizontal: 14 },
  signInButton: {
    alignItems: "center",
    backgroundColor: "#FFC21C",
    borderRadius: 11,
    elevation: 4,
    justifyContent: "center",
    height: 50,
    marginTop: 8,
    shadowColor: "#001B51",
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
  },
  signInText: { color: "#071327", fontSize: 17, fontWeight: "800" },
  signInButtonDisabled: { opacity: 0.7 },
  loginError: { color: "#FFD1D1", fontSize: 12, fontWeight: "600", marginBottom: 8, textAlign: "center" },
  continueRow: { alignItems: "center", flexDirection: "row", gap: 12, marginTop: 18 },
  divider: { backgroundColor: "rgba(255, 255, 255, 0.42)", flex: 1, height: 1 },
  continueText: { color: "#FFFFFF", fontSize: 12 },
  alternativeRow: { flexDirection: "row", justifyContent: "center", gap: 34, marginTop: 17 },
  alternativeButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 27,
    elevation: 3,
    height: 52,
    justifyContent: "center",
    shadowColor: "#001B51",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 5,
    width: 52,
  },
  faceScanner: { height: 34, position: "relative", width: 34 },
  scanCorner: { borderColor: "#003D9C", height: 10, position: "absolute", width: 10 },
  scanTopLeft: { borderLeftWidth: 3, borderTopLeftRadius: 5, borderTopWidth: 3, left: 1, top: 1 },
  scanTopRight: { borderRightWidth: 3, borderTopRightRadius: 5, borderTopWidth: 3, right: 1, top: 1 },
  scanBottomLeft: { borderBottomLeftRadius: 5, borderBottomWidth: 3, borderLeftWidth: 3, bottom: 1, left: 1 },
  scanBottomRight: { borderBottomRightRadius: 5, borderBottomWidth: 3, borderRightWidth: 3, bottom: 1, right: 1 },
  faceEye: { backgroundColor: "#003D9C", borderRadius: 3, height: 5, position: "absolute", top: 11, width: 5 },
  faceLeftEye: { left: 9 },
  faceRightEye: { right: 9 },
  faceSmile: { borderBottomColor: "#003D9C", borderBottomWidth: 4, borderRadius: 10, bottom: 8, height: 9, left: 10, position: "absolute", width: 14 },
  signupRow: { alignItems: "center", flexDirection: "row", justifyContent: "center", marginTop: 34 },
  signupText: { color: "#FFFFFF", fontSize: 12 },
  signupLink: { color: "#FFC21C", fontSize: 12, fontWeight: "700" },
});
