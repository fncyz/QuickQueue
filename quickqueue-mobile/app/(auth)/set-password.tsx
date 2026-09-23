import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { setInitialPassword } from '@/services/api';

export default function SetPasswordScreen() {
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!password || !confirmation) return Alert.alert('Password required', 'Enter and confirm your new password.');
    if (password !== confirmation) return Alert.alert('Passwords do not match', 'Enter the same password in both fields.');
    try {
      setSaving(true);
      const token = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!token) return router.replace('/login');
      await setInitialPassword(token, password, confirmation);
      await AsyncStorage.removeItem('quickqueue.requiresInitialPassword');
      Alert.alert('Password secured', 'Your new password has been saved. Please keep it somewhere safe.', [
        { text: 'Continue', onPress: () => router.replace('/(tabs)') },
      ]);
    } catch (error: any) {
      Alert.alert('Password not saved', error?.response?.data?.message || 'Please try again.');
    } finally { setSaving(false); }
  };

  return <SafeAreaView style={s.safe} edges={['top', 'bottom']}><KeyboardAvoidingView style={s.keyboard} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
    <View style={s.icon}><Ionicons name="shield-checkmark" size={54} color="#0759D9" /></View>
    <Text style={s.title}>Secure Your Account</Text>
    <Text style={s.description}>Before continuing, create a password that only you know. This replaces the temporary password generated during registration.</Text>
    <View style={s.notice}><Ionicons name="information-circle-outline" size={21} color="#0759D9" /><Text style={s.noticeText}>You do not need to enter your temporary password again.</Text></View>
    <PasswordField label="New Password" value={password} onChangeText={setPassword} visible={showPassword} onToggle={() => setShowPassword((value) => !value)} />
    <PasswordField label="Confirm New Password" value={confirmation} onChangeText={setConfirmation} visible={showConfirmation} onToggle={() => setShowConfirmation((value) => !value)} />
    <View style={s.rules}><Text style={s.rulesTitle}>Create a strong password:</Text><Text style={s.rule}>• Use at least 6 characters</Text><Text style={s.rule}>• Avoid using your username or personal information</Text><Text style={s.rule}>• Save it somewhere secure so you do not lose access</Text></View>
    <Pressable onPress={submit} disabled={saving} style={[s.button, saving && s.disabled]}><Text style={s.buttonText}>{saving ? 'Saving Password...' : 'Save Password & Continue'}</Text></Pressable>
  </ScrollView></KeyboardAvoidingView></SafeAreaView>;
}

function PasswordField({ label, value, onChangeText, visible, onToggle }: { label: string; value: string; onChangeText: (value: string) => void; visible: boolean; onToggle: () => void }) { return <View style={s.field}><Text style={s.label}>{label}</Text><View style={s.inputShell}><Ionicons name="lock-closed-outline" size={20} color="#0759D9" /><TextInput style={s.input} value={value} onChangeText={onChangeText} secureTextEntry={!visible} autoCapitalize="none" autoCorrect={false} placeholder="Enter your new password" placeholderTextColor="#8A94A8" /><Pressable onPress={onToggle} style={s.eye}><Ionicons name={visible ? 'eye-off-outline' : 'eye-outline'} size={22} color="#0759D9" /></Pressable></View></View>; }

const s = StyleSheet.create({ safe: { backgroundColor: '#07419C', flex: 1 }, keyboard: { flex: 1 }, content: { backgroundColor: '#FFF', flexGrow: 1, justifyContent: 'center', paddingHorizontal: 27, paddingVertical: 34 }, icon: { alignItems: 'center', alignSelf: 'center', backgroundColor: '#EDF4FF', borderRadius: 48, height: 96, justifyContent: 'center', width: 96 }, title: { color: '#123A7C', fontSize: 25, fontWeight: '800', marginTop: 20, textAlign: 'center' }, description: { color: '#5E687C', fontSize: 13, lineHeight: 20, marginTop: 9, textAlign: 'center' }, notice: { alignItems: 'center', backgroundColor: '#EFF5FF', borderLeftColor: '#0759D9', borderLeftWidth: 3, borderRadius: 8, flexDirection: 'row', gap: 9, marginTop: 22, padding: 12 }, noticeText: { color: '#365074', flex: 1, fontSize: 11, lineHeight: 16 }, field: { marginTop: 19 }, label: { color: '#233452', fontSize: 12, fontWeight: '700', marginBottom: 7 }, inputShell: { alignItems: 'center', borderColor: '#D7DFEC', borderRadius: 10, borderWidth: 1, flexDirection: 'row', height: 54, paddingLeft: 13 }, input: { color: '#18233C', flex: 1, fontSize: 14, height: '100%', paddingHorizontal: 11 }, eye: { alignItems: 'center', height: '100%', justifyContent: 'center', paddingHorizontal: 13 }, rules: { backgroundColor: '#F7F9FD', borderRadius: 9, marginTop: 18, padding: 13 }, rulesTitle: { color: '#233452', fontSize: 11, fontWeight: '800', marginBottom: 5 }, rule: { color: '#667187', fontSize: 10, lineHeight: 16 }, button: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 10, marginTop: 22, paddingVertical: 15 }, disabled: { opacity: 0.65 }, buttonText: { color: '#FFF', fontSize: 14, fontWeight: '800' } });
