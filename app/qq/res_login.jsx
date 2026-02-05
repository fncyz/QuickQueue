import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { BlurView } from 'expo-blur'
import { useRouter } from 'expo-router'
import { useState } from 'react'

const ResLogin = () => {
  const router = useRouter()
  const [loginType, setLoginType] = useState('resident')
  const [emailOrPhone, setEmailOrPhone] = useState('')
  const [password, setPassword] = useState('')

  const handleSignIn = () => {
    // TODO: Implement sign-in logic
  }

  const handleSignUp = () => {
    // TODO: Navigate to sign-up screen when available
    router.push('/qq/signup')
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Blurred background - Index page content */}
      <View style={styles.backgroundContainer} pointerEvents="none">
        <BlurView intensity={50} tint="natural" style={styles.blurOverlay}>
          <ScrollView 
            style={styles.backgroundScroll}
            contentContainerStyle={styles.backgroundContent}
          >
            {/* Header */}
            <View style={styles.backgroundHeader}></View>

            {/* Main Content Area */}
            <View style={styles.backgroundMainContent}>
              <View style={styles.backgroundLogoTitleContainer}>
                {/* Logo */}
                <Image 
                  source={require('../../assets/images/logo.png')} 
                  style={styles.backgroundLogo}
                  resizeMode="contain"
                />
                
                {/* Title */}
                <View style={styles.backgroundTitleContainer}>
                  <Text style={styles.backgroundTitle}>
                    <Text style={styles.backgroundTitleYellow}>Q</Text>
                    uick<Text style={styles.backgroundTitleRed}>Q</Text>ueue
                  </Text>
                  <Text style={styles.backgroundTagline}>
                    A Smart Online Appointment and Queue Management System for Baranggays
                  </Text>
                </View>
              </View>

              {/* Buttons */}
              <View style={styles.backgroundButtonContainer}>
                <View style={[styles.backgroundButton, styles.backgroundDownloadButton]}>
                  <Text style={styles.backgroundDownloadButtonText}>Download</Text>
                </View>
                
                <View style={[styles.backgroundButton, styles.backgroundGetStartedButton]}>
                  <Text style={styles.backgroundGetStartedButtonText}>Get Started</Text>
                </View>
              </View>
            </View>

            {/* Footer */}
            <View style={styles.backgroundFooter}>
              <Text style={styles.backgroundFooterText}>
                © Consolatrix College of Toledo City. All rights Reserved.
              </Text>
            </View>
          </ScrollView>
        </BlurView>
        {/* White overlay for color scheme */}
        <View style={styles.whiteOverlay} />
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Central login card */}
          <View style={styles.card}>
            {/* Logo */}
            <View style={styles.logoContainer}>
              <Image
                source={require('../../assets/images/qq-logo.png')}
                style={styles.logoImage}
                resizeMode="contain"
              />
            </View>

            {/* Welcome */}
            <Text style={styles.welcomeTitle}>WELCOME!</Text>
            <Text style={styles.welcomeSubtext}>
              Sign in to manage appointments and queues.
            </Text>

            {/* Login type selector */}
            <View style={styles.loginTypeRow}>
              <Pressable
                style={[
                  styles.loginTypeOption,
                  loginType === 'resident' ? styles.loginTypeBtnActive : styles.loginTypeLinkWrap,
                ]}
                onPress={() => setLoginType('resident')}
              >
                <Text
                  style={[
                    loginType === 'resident' ? styles.loginTypeBtnTextActive : styles.loginTypeLinkText,
                  ]}
                >
                  Resident Login
                </Text>
              </Pressable>
              <Pressable
                style={[
                  styles.loginTypeOption,
                  loginType === 'admin' ? styles.loginTypeBtnActive : styles.loginTypeLinkWrap,
                ]}
                onPress={() => setLoginType('admin')}
              >
                <Text
                  style={[
                    loginType === 'admin' ? styles.loginTypeBtnTextActive : styles.loginTypeLinkText,
                  ]}
                >
                  Admin Login
                </Text>
              </Pressable>
            </View>

            {/* Inputs */}
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email or Phone Number</Text>
              <TextInput
                style={styles.input}
                placeholder=""
                placeholderTextColor="#9ca3af"
                value={emailOrPhone}
                onChangeText={setEmailOrPhone}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Password</Text>
              <TextInput
                style={styles.input}
                placeholder=""
                placeholderTextColor="#9ca3af"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
            </View>

            {/* Sign In */}
            <Pressable style={styles.signInBtn} onPress={handleSignIn}>
              <Text style={styles.signInBtnText}>Sign In</Text>
            </Pressable>

            {/* Sign Up link */}
            <View style={styles.signUpRow}>
              <Text style={styles.signUpPrompt}>Don't have an account?</Text>
              <Pressable onPress={handleSignUp}>
                <Text style={styles.signUpLink}>Sign Up</Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

export default ResLogin

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a237e',
  },
  backgroundContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  blurOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    opacity: 0.3,
  },
  whiteOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#ffffff',
    opacity: 0.2,
  },
  backgroundScroll: {
    flex: 1,
  },
  backgroundContent: {
    flexGrow: 1,
  },
  backgroundHeader: {
    backgroundColor: '#1a237e',
    height: 60,
    width: '100%',
    opacity: 0.3,
  },
  backgroundMainContent: {
    flex: 1,
    backgroundColor: '#2196F3',
    paddingHorizontal: 20,
    paddingVertical: 40,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 500,
    opacity: 0.3,
  },
  backgroundLogoTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 40,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  backgroundLogo: {
    width: 200,
    height: 200,
    marginRight: 20,
    opacity: 0.3,
  },
  backgroundTitleContainer: {
    flex: 1,
    minWidth: 250,
    alignItems: 'center',
  },
  backgroundTitle: {
    fontSize: 42,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
    textAlign: 'center',
    opacity: 0.3,
  },
  backgroundTitleYellow: {
    color: '#FFD700',
  },
  backgroundTitleRed: {
    color: '#FF0000',
  },
  backgroundTagline: {
    fontSize: 20,
    color: '#FFFFFF',
    lineHeight: 28,
    textAlign: 'center',
    opacity: 0.3,
  },
  backgroundButtonContainer: {
    flexDirection: 'row',
    gap: 20,
    marginTop: 20,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  backgroundButton: {
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 8,
    minWidth: 140,
    alignItems: 'center',
    opacity: 0.3,
  },
  backgroundDownloadButton: {
    backgroundColor: '#FF0000',
  },
  backgroundDownloadButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  backgroundGetStartedButton: {
    backgroundColor: '#FFD700',
  },
  backgroundGetStartedButtonText: {
    color: '#1e1e61',
    fontSize: 18,
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  backgroundFooter: {
    backgroundColor: '#1a237e',
    paddingVertical: 20,
    width: '100%',
    alignItems: 'center',
    opacity: 0.3,
  },
  backgroundFooterText: {
    color: '#FFFFFF',
    fontSize: 14,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 32,
    paddingTop: 20,
    paddingBottom: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#ffffff',
    borderRadius: 24,
    paddingHorizontal: 28,
    paddingVertical: 32,
    alignItems: 'center',
    alignSelf: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.3,
    shadowRadius: 32,
    elevation: 20,
    zIndex: 10,
  },
  logoContainer: {
    marginBottom: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoImage: {
    width: 88,
    height: 88,
  },
  welcomeTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#0f172a',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  welcomeSubtext: {
    fontSize: 15,
    color: '#64748b',
    marginBottom: 24,
    textAlign: 'center',
  },
  loginTypeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginBottom: 24,
  },
  loginTypeOption: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 999,
  },
  loginTypeLinkWrap: {
    backgroundColor: 'transparent',
  },
  loginTypeBtnActive: {
    backgroundColor: '#1e3a8a',
  },
  loginTypeBtnTextActive: {
    fontSize: 15,
    color: '#ffffff',
    fontWeight: '600',
  },
  loginTypeLinkText: {
    fontSize: 15,
    color: '#2563eb',
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  inputGroup: {
    width: '100%',
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 14,
    color: '#475569',
    marginBottom: 8,
    fontWeight: '500',
  },
  input: {
    width: '100%',
    backgroundColor: '#e0e7ff',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#0f172a',
  },
  signInBtn: {
    width: '100%',
    backgroundColor: '#1e3a8a',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 24,
  },
  signInBtnText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#ffffff',
  },
  signUpRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  signUpPrompt: {
    fontSize: 15,
    color: '#64748b',
  },
  signUpLink: {
    fontSize: 15,
    color: '#2563eb',
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
})
