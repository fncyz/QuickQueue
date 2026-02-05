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
  Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { BlurView } from 'expo-blur'
import { useRouter } from 'expo-router'
import { useState } from 'react'

import { createUserWithEmailAndPassword } from 'firebase/auth'
import { doc, setDoc } from 'firebase/firestore'
import { auth, db } from '../../firebaseConfig'

const SignUp = () => {
  const router = useRouter()

  // 🔐 Auth
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loginType] = useState('resident')

  // 👤 User Info
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [lastName, setLastName] = useState('')
  const [contactNumber, setContactNumber] = useState('')
  const [address, setAddress] = useState('')

  const handleCreateAcc = async () => {
    if (!email || !password || !confirmPassword || !firstName || !lastName) {
      Alert.alert('Error', 'Please fill in all required fields')
      return
    }

    if (password !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match')
      return
    }

    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email.trim(),
        password
      )

      const user = userCredential.user

      await setDoc(doc(db, 'users', user.uid), {
        uid: user.uid,
        email: user.email,
        role: loginType,
        firstName,
        middleName,
        lastName,
        contactNumber,
        address,
        createdAt: new Date(),
      })

      Alert.alert('Success', 'Account created successfully')
      router.replace('/qq/res_login')
    } catch (error) {
      Alert.alert('Signup Failed', error.message)
    }
  }

  const handleSignIn = () => {
    router.push('/qq/res_login')
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* 🔽 EVERYTHING BELOW IS YOUR ORIGINAL UI */}
      <View style={styles.backgroundContainer} pointerEvents="none">
        <BlurView intensity={50} tint="natural" style={styles.blurOverlay}>
          <ScrollView
            style={styles.backgroundScroll}
            contentContainerStyle={styles.backgroundContent}
          >
            <View style={styles.backgroundHeader}></View>

            <View style={styles.backgroundMainContent}>
              <View style={styles.backgroundLogoTitleContainer}>
                <Image
                  source={require('../../assets/images/logo.png')}
                  style={styles.backgroundLogo}
                  resizeMode="contain"
                />
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

              <View style={styles.backgroundButtonContainer}>
                <View style={[styles.backgroundButton, styles.backgroundDownloadButton]}>
                  <Text style={styles.backgroundDownloadButtonText}>Download</Text>
                </View>
                <View style={[styles.backgroundButton, styles.backgroundGetStartedButton]}>
                  <Text style={styles.backgroundGetStartedButtonText}>Get Started</Text>
                </View>
              </View>
            </View>

            <View style={styles.backgroundFooter}>
              <Text style={styles.backgroundFooterText}>
                © Consolatrix College of Toledo City. All rights Reserved.
              </Text>
            </View>
          </ScrollView>
        </BlurView>
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
          <View style={styles.card}>
            <Text style={styles.welcomeTitle}>Create Account</Text>
            <Text style={styles.welcomeSubtext}>Join us to get Started!</Text>

            {/* Inputs */}
            <View style={styles.row}>
              <View style={styles.inputFirst}>
                <Text style={styles.inputLabel}>First Name</Text>
                <TextInput style={styles.input} value={firstName} onChangeText={setFirstName} />
              </View>

              <View style={styles.inputMid}>
                <Text style={styles.inputLabel}>Middle Name</Text>
                <TextInput style={styles.input} value={middleName} onChangeText={setMiddleName} />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Last Name</Text>
              <TextInput style={styles.input} value={lastName} onChangeText={setLastName} />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email Address</Text>
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Contact Number</Text>
              <TextInput
                style={styles.input}
                value={contactNumber}
                onChangeText={setContactNumber}
                keyboardType="phone-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Baranggay Address</Text>
              <TextInput style={styles.input} value={address} onChangeText={setAddress} />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Password</Text>
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Confirm Password</Text>
              <TextInput
                style={styles.input}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry
              />
            </View>

            <Pressable style={styles.signInBtn} onPress={handleCreateAcc}>
              <Text style={styles.signInBtnText}>Create Account</Text>
            </Pressable>

            <View style={styles.signUpRow}>
              <Text style={styles.signUpPrompt}>Already have an Account?</Text>
              <Pressable onPress={handleSignIn}>
                <Text style={styles.signUpLink}>Sign In</Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

export default SignUp

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
    maxWidth: 980,
    backgroundColor: '#ffffff',
    borderRadius: 30,
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
  welcomeTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#193f89',
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
  row: {
    flexDirection: 'row',
    gap: 15,        // space between the inputs
    marginBottom: 20,
 },
 inputFirst: {
    flex: 3,        // bigger

 },
 inputMid: {
    flex: 1,        // smaller
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
    borderRadius: 25,
  },
  signInBtn: {
    width: '100%',
    backgroundColor: '#1e3a8a',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 24,
    borderRadius: 25,
  },
  signInBtnText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#ffffff',
    textDecorationLine: 'underline',
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
