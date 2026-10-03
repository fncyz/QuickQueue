import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, AppState, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Text } from '@/components/Typography';
import { useAppTheme } from '@/contexts/app-theme';
import { getPushPermissionState, openNotificationSettings, PushPermissionState, registerForPushNotifications } from '@/services/push-notifications';

export default function NotificationSettingsScreen() {
  const { colors } = useAppTheme();
  const [state, setState] = useState<PushPermissionState>('undetermined');
  const refresh = useCallback(() => { getPushPermissionState().then(setState); }, []);
  useEffect(() => { refresh(); const subscription = AppState.addEventListener('change', (value) => value === 'active' && refresh()); return () => subscription.remove(); }, [refresh]);

  const enable = () => Alert.alert(
    'Allow QuickQueue notifications?',
    'Receive appointment, check-in, and queue updates. Notification previews avoid unnecessary personal information.',
    [{ text: 'Not Now', style: 'cancel' }, { text: 'Continue', onPress: async () => {
      const result = await registerForPushNotifications(true);
      setState(result.state);
      if (result.state === 'unavailable') Alert.alert('Notifications unavailable', result.message || 'Use a physical device and a development or production build.');
    } }],
  );

  const enabled = state === 'granted';
  const label = enabled ? 'Enabled' : state === 'denied' ? 'Blocked in device settings' : state === 'unavailable' ? 'Unavailable on this build/device' : 'Not enabled';
  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]}><View style={[s.header, { backgroundColor: colors.primary }]}><Pressable onPress={() => router.back()}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable><Text style={s.heading}>Push Notifications</Text></View><View style={s.body}><View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Ionicons name={enabled ? 'notifications' : 'notifications-off-outline'} size={32} color={enabled ? '#159447' : colors.muted} /><Text style={[s.title, { color: colors.text }]}>Device notifications</Text><Text style={[s.status, { color: enabled ? '#159447' : '#C45B00' }]}>{label}</Text><Text style={[s.copy, { color: colors.muted }]}>QuickQueue can alert you about appointment decisions, check-in, queue progress, and completed transactions. Your device’s Silent Mode and Do Not Disturb settings are always respected.</Text>{!enabled && <Pressable onPress={state === 'denied' ? openNotificationSettings : enable} style={s.button}><Text style={s.buttonText}>{state === 'denied' ? 'Open Device Settings' : 'Enable Notifications'}</Text></Pressable>}</View></View></SafeAreaView>;
}

const s = StyleSheet.create({ safe: { flex: 1 }, header: { alignItems: 'center', flexDirection: 'row', gap: 14, minHeight: 82, paddingHorizontal: 18 }, heading: { color: '#FFF', fontSize: 20, fontWeight: '800' }, body: { padding: 16 }, card: { alignItems: 'center', borderRadius: 16, borderWidth: 1, padding: 12 }, title: { fontSize: 14, fontWeight: '600', marginTop: 6 }, status: { fontSize: 10, fontWeight: '500', marginTop: 2 }, copy: { fontSize: 10, lineHeight: 16, marginTop: 8, textAlign: 'center' }, button: { backgroundColor: '#0873FF', borderRadius: 9, marginTop: 12, minHeight: 38, paddingHorizontal: 17, paddingVertical: 8 }, buttonText: { color: '#FFF', fontSize: 10, fontWeight: '600' } });
