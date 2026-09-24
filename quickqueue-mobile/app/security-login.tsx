import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import * as LocalAuthentication from 'expo-local-authentication';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { SuccessAnimation } from '@/components/SuccessAnimation';
import { useAppTheme } from '@/contexts/app-theme';
import { changePassword, changeSecurityPin, verifyAccountPassword, verifySecurityPin } from '@/services/api';
import { BiometricKind, disableBiometricLogin, enableBiometricLogin, getBiometricStatuses } from '@/services/secure-auth';

export default function SecurityLoginScreen() {
  const { colors } = useAppTheme();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [statuses, setStatuses] = useState({ fingerprint: false, face: false });
  const [biometricKind, setBiometricKind] = useState<BiometricKind | null>(null);
  const [verificationPin, setVerificationPin] = useState('');
  const [passwordForPin, setPasswordForPin] = useState('');
  const [passwordVerified, setPasswordVerified] = useState(false);
  const [newPin, setNewPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [pinSuccess, setPinSuccess] = useState(false);

  useEffect(() => { getBiometricStatuses().then(setStatuses); }, []);

  const accessToken = async () => {
    const token = await AsyncStorage.getItem('quickqueue.accessToken');
    if (!token) router.replace('/login');
    return token;
  };

  const updatePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) return Alert.alert('Missing information', 'Complete all password fields.');
    const token = await accessToken(); if (!token) return;
    try {
      setSaving(true);
      await changePassword(token, currentPassword, newPassword, confirmPassword);
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('');
      Alert.alert('Password updated', 'Use your new password the next time you sign in.');
    } catch (error: any) { Alert.alert('Password not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  const beginBiometric = (kind: BiometricKind) => {
    if (statuses[kind]) return disableKind(kind);
    setVerificationPin('');
    setBiometricKind(kind);
  };

  const enableKind = async () => {
    if (!biometricKind || !/^\d{4}$/.test(verificationPin)) return Alert.alert('Invalid PIN', 'Enter your 4-digit PIN.');
    const token = await accessToken(); if (!token) return;
    try {
      setSaving(true);
      await verifySecurityPin(token, verificationPin);
      const supported = await LocalAuthentication.supportedAuthenticationTypesAsync();
      const requiredType = biometricKind === 'fingerprint' ? LocalAuthentication.AuthenticationType.FINGERPRINT : LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION;
      if (!supported.includes(requiredType)) throw new Error(`${biometricKind === 'fingerprint' ? 'Fingerprint' : 'Face recognition'} is not supported on this device.`);
      if (!await LocalAuthentication.isEnrolledAsync()) throw new Error('Set up this biometric in your device settings first.');
      const result = await LocalAuthentication.authenticateAsync({ promptMessage: `Enable ${biometricKind === 'fingerprint' ? 'Fingerprint' : 'Face Recognition'}`, disableDeviceFallback: true });
      if (!result.success) return;
      const refreshToken = await AsyncStorage.getItem('quickqueue.refreshToken');
      if (!refreshToken) throw new Error('Please sign in again before enabling biometric login.');
      await enableBiometricLogin(biometricKind, refreshToken);
      setStatuses((current) => ({ ...current, [biometricKind]: true }));
      setBiometricKind(null); setVerificationPin('');
      Alert.alert('Biometric login enabled', `${biometricKind === 'fingerprint' ? 'Fingerprint' : 'Face recognition'} can now be used to sign in.`);
    } catch (error: any) { Alert.alert('Could not enable biometric login', error?.response?.data?.message || error?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  const disableKind = async (kind: BiometricKind) => {
    await disableBiometricLogin(kind);
    setStatuses((current) => ({ ...current, [kind]: false }));
    Alert.alert('Biometric login disabled', `${kind === 'fingerprint' ? 'Fingerprint' : 'Face recognition'} login has been disabled.`);
  };

  const verifyPassword = async () => {
    if (!passwordForPin) return Alert.alert('Password required', 'Enter your account password first.');
    const token = await accessToken(); if (!token) return;
    try { setSaving(true); await verifyAccountPassword(token, passwordForPin); setPasswordVerified(true); }
    catch (error: any) { Alert.alert('Verification failed', error?.response?.data?.message || 'Your PIN has not been changed.'); }
    finally { setSaving(false); }
  };

  const updatePin = async () => {
    if (!/^\d{4}$/.test(newPin)) return Alert.alert('Invalid PIN', 'The new PIN must contain exactly 4 numeric digits.');
    if (newPin !== confirmPin) return Alert.alert('PINs do not match', 'Your existing PIN has not been changed.');
    const token = await accessToken(); if (!token) return;
    try {
      setSaving(true);
      await changeSecurityPin(token, passwordForPin, newPin, confirmPin);
      setPasswordForPin(''); setNewPin(''); setConfirmPin(''); setPasswordVerified(false); setPinSuccess(true);
      setTimeout(() => setPinSuccess(false), 2200);
    } catch (error: any) { Alert.alert('PIN not changed', error?.response?.data?.message || 'Your existing PIN has not been changed.'); }
    finally { setSaving(false); }
  };

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
    <View style={[s.header, { backgroundColor: colors.primary }]}><Pressable accessibilityLabel="Back to profile" onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={25} color="#FFF" /></Pressable><Text style={s.heading}>Security & Login</Text></View>
    <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <Section title="Biometric Login" copy="Choose which device biometrics can be used to sign in." colors={colors}>
        <BiometricRow label="Fingerprint" icon="finger-print" enabled={statuses.fingerprint} onPress={() => beginBiometric('fingerprint')} colors={colors} />
        <BiometricRow label="Face Recognition" icon="scan-outline" enabled={statuses.face} onPress={() => beginBiometric('face')} colors={colors} />
        {biometricKind && <View style={[s.verifyBox, { borderColor: colors.border }]}><Text style={[s.label, { color: colors.text }]}>Enter your 4-digit PIN to enable {biometricKind === 'fingerprint' ? 'Fingerprint' : 'Face Recognition'}</Text><PinInput value={verificationPin} onChangeText={setVerificationPin} colors={colors} /><View style={s.inlineActions}><Pressable onPress={() => setBiometricKind(null)} style={s.cancel}><Text style={[s.cancelText, { color: colors.muted }]}>Cancel</Text></Pressable><Pressable disabled={saving} onPress={enableKind} style={s.compactSave}><Text style={s.saveText}>Verify & Enable</Text></Pressable></View></View>}
      </Section>
      <Section title="Change 4-Digit PIN" copy="Verify your account password before choosing a new PIN." colors={colors}>
        {pinSuccess ? <View style={s.success}><SuccessAnimation size={74} /><Text style={[s.successText, { color: colors.text }]}>PIN Changed Successfully!</Text></View> : !passwordVerified ? <><PasswordInput label="Account Password" value={passwordForPin} onChangeText={setPasswordForPin} colors={colors} /><Pressable disabled={saving} onPress={verifyPassword} style={s.save}><Text style={s.saveText}>{saving ? 'Verifying...' : 'Verify Password'}</Text></Pressable></> : <><PinInput label="New 4-Digit PIN" value={newPin} onChangeText={setNewPin} colors={colors} /><PinInput label="Confirm New PIN" value={confirmPin} onChangeText={setConfirmPin} colors={colors} /><Pressable disabled={saving} onPress={updatePin} style={s.save}><Text style={s.saveText}>{saving ? 'Changing...' : 'Change PIN'}</Text></Pressable></>}
      </Section>
      <Section title="Change Password" copy="Update your password to keep your account secure." colors={colors}>
        <PasswordInput label="Current Password" value={currentPassword} onChangeText={setCurrentPassword} colors={colors} />
        <PasswordInput label="New Password" value={newPassword} onChangeText={setNewPassword} colors={colors} />
        <PasswordInput label="Confirm New Password" value={confirmPassword} onChangeText={setConfirmPassword} colors={colors} />
        <Pressable disabled={saving} onPress={updatePassword} style={s.save}><Text style={s.saveText}>{saving ? 'Updating...' : 'Update Password'}</Text></Pressable>
      </Section>
    </ScrollView>
  </SafeAreaView>;
}

function Section({ title, copy, colors, children }: { title: string; copy: string; colors: typeof import('@/contexts/app-theme').lightPalette; children: React.ReactNode }) { return <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={[s.title, { color: colors.text }]}>{title}</Text><Text style={[s.copy, { color: colors.muted }]}>{copy}</Text>{children}</View>; }
function PasswordInput({ label, value, onChangeText, colors }: { label: string; value: string; onChangeText: (value: string) => void; colors: typeof import('@/contexts/app-theme').lightPalette }) { return <View style={s.field}><Text style={[s.label, { color: colors.text }]}>{label}</Text><TextInput style={[s.input, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={value} onChangeText={onChangeText} secureTextEntry placeholder="Enter password" placeholderTextColor={colors.muted} /></View>; }
function PinInput({ label, value, onChangeText, colors }: { label?: string; value: string; onChangeText: (value: string) => void; colors: typeof import('@/contexts/app-theme').lightPalette }) { return <View style={s.field}>{label && <Text style={[s.label, { color: colors.text }]}>{label}</Text>}<TextInput style={[s.input, s.pinInput, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={value} onChangeText={(text) => onChangeText(text.replace(/\D/g, '').slice(0, 4))} secureTextEntry keyboardType="number-pad" maxLength={4} placeholder="••••" placeholderTextColor={colors.muted} /></View>; }
function BiometricRow({ label, icon, enabled, onPress, colors }: { label: string; icon: keyof typeof Ionicons.glyphMap; enabled: boolean; onPress: () => void; colors: typeof import('@/contexts/app-theme').lightPalette }) { return <View style={[s.biometricRow, { borderColor: colors.border }]}><View style={[s.bioIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={icon} size={23} color={colors.accent} /></View><View style={s.bioCopy}><Text style={[s.bioTitle, { color: colors.text }]}>{label}</Text><Text style={[s.status, { color: enabled ? '#159447' : colors.muted }]}>{enabled ? 'Enabled' : 'Disabled'}</Text></View><Pressable onPress={onPress} style={[s.toggleButton, enabled && s.disableButton]}><Text style={[s.toggleText, enabled && s.disableText]}>{enabled ? 'Disable' : 'Enable'}</Text></Pressable></View>; }

const s = StyleSheet.create({ safe: { flex: 1 }, header: { alignItems: 'center', flexDirection: 'row', minHeight: 82, paddingHorizontal: 16 }, back: { padding: 8 }, heading: { color: '#FFF', fontSize: 20, fontWeight: '800', marginLeft: 12 }, content: { padding: 16, paddingBottom: 30 }, card: { borderRadius: 16, borderWidth: 1, marginBottom: 14, padding: 18 }, title: { fontSize: 17, fontWeight: '800' }, copy: { fontSize: 12, marginBottom: 18, marginTop: 5 }, field: { marginBottom: 13 }, label: { fontSize: 11, fontWeight: '700', marginBottom: 6 }, input: { borderRadius: 9, borderWidth: 1, fontSize: 13, height: 46, paddingHorizontal: 12 }, pinInput: { fontSize: 20, letterSpacing: 10, textAlign: 'center' }, save: { alignItems: 'center', backgroundColor: '#0873FF', borderRadius: 9, marginTop: 5, paddingVertical: 13 }, saveText: { color: '#FFF', fontSize: 11, fontWeight: '800' }, biometricRow: { alignItems: 'center', borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 64 }, bioIcon: { alignItems: 'center', borderRadius: 19, height: 38, justifyContent: 'center', width: 38 }, bioCopy: { flex: 1, marginLeft: 11 }, bioTitle: { fontSize: 12, fontWeight: '800' }, status: { fontSize: 10, fontWeight: '700', marginTop: 3 }, toggleButton: { backgroundColor: '#0873FF', borderRadius: 8, paddingHorizontal: 14, paddingVertical: 9 }, toggleText: { color: '#FFF', fontSize: 10, fontWeight: '800' }, disableButton: { backgroundColor: '#FFE8EB' }, disableText: { color: '#D62D3B' }, verifyBox: { borderTopWidth: StyleSheet.hairlineWidth, marginTop: 8, paddingTop: 15 }, inlineActions: { flexDirection: 'row', gap: 9, justifyContent: 'flex-end' }, cancel: { justifyContent: 'center', paddingHorizontal: 12 }, cancelText: { fontSize: 11, fontWeight: '700' }, compactSave: { backgroundColor: '#0873FF', borderRadius: 8, paddingHorizontal: 14, paddingVertical: 11 }, success: { alignItems: 'center', paddingVertical: 8 }, successText: { fontSize: 14, fontWeight: '800', marginTop: 12 } });
