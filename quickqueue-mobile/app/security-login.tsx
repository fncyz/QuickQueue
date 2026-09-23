import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAppTheme } from '@/contexts/app-theme';
import { changePassword } from '@/services/api';

export default function SecurityLoginScreen() {
  const { colors } = useAppTheme();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);

  const updatePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) return Alert.alert('Missing information', 'Complete all password fields.');
    const token = await AsyncStorage.getItem('quickqueue.accessToken');
    if (!token) return router.replace('/login');
    try {
      setSaving(true);
      await changePassword(token, currentPassword, newPassword, confirmPassword);
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('');
      Alert.alert('Password updated', 'Use your new password the next time you sign in.');
    } catch (error: any) { Alert.alert('Password not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
    <View style={[s.header, { backgroundColor: colors.primary }]}><Pressable accessibilityLabel="Back to profile" onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={25} color="#FFF" /></Pressable><Text style={s.heading}>Security & Login</Text></View>
    <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={[s.title, { color: colors.text }]}>Change Password</Text><Text style={[s.copy, { color: colors.muted }]}>Update your password to keep your account secure.</Text>
      <PasswordInput label="Current Password" value={currentPassword} onChangeText={setCurrentPassword} colors={colors} />
      <PasswordInput label="New Password" value={newPassword} onChangeText={setNewPassword} colors={colors} />
      <PasswordInput label="Confirm New Password" value={confirmPassword} onChangeText={setConfirmPassword} colors={colors} />
      <Pressable disabled={saving} onPress={updatePassword} style={s.save}><Text style={s.saveText}>{saving ? 'Updating...' : 'Update Password'}</Text></Pressable>
    </View>
  </SafeAreaView>;
}

function PasswordInput({ label, value, onChangeText, colors }: { label: string; value: string; onChangeText: (value: string) => void; colors: typeof import('@/contexts/app-theme').lightPalette }) { return <View style={s.field}><Text style={[s.label, { color: colors.text }]}>{label}</Text><TextInput style={[s.input, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={value} onChangeText={onChangeText} secureTextEntry placeholder="Enter password" placeholderTextColor={colors.muted} /></View>; }
const s = StyleSheet.create({ safe: { flex: 1 }, header: { alignItems: 'center', flexDirection: 'row', minHeight: 82, paddingHorizontal: 16 }, back: { padding: 8 }, heading: { color: '#FFF', fontSize: 20, fontWeight: '800', marginLeft: 12 }, card: { borderRadius: 16, borderWidth: 1, margin: 16, padding: 18 }, title: { fontSize: 17, fontWeight: '800' }, copy: { fontSize: 12, marginBottom: 22, marginTop: 5 }, field: { marginBottom: 13 }, label: { fontSize: 11, fontWeight: '700', marginBottom: 6 }, input: { borderRadius: 9, borderWidth: 1, fontSize: 13, height: 46, paddingHorizontal: 12 }, save: { alignItems: 'center', backgroundColor: '#0873FF', borderRadius: 9, marginTop: 5, paddingVertical: 13 }, saveText: { color: '#FFF', fontSize: 12, fontWeight: '800' } });
