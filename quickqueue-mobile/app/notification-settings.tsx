import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, AppState, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Text } from '@/components/Typography';
import { useAppTheme } from '@/contexts/app-theme';
import {
  getPushDeviceRegistrationStatus,
  getPushPermissionState,
  openNotificationSettings,
  PushDeviceRegistrationStatus,
  PushPermissionState,
  registerForPushNotifications,
} from '@/services/push-notifications';

export default function NotificationSettingsScreen() {
  const { colors } = useAppTheme();
  const [permission, setPermission] = useState<PushPermissionState>('undetermined');
  const [registration, setRegistration] = useState<PushDeviceRegistrationStatus>({ state: 'unavailable', registered: false });
  const [registering, setRegistering] = useState(false);

  const refresh = useCallback(() => {
    getPushPermissionState().then(setPermission);
    getPushDeviceRegistrationStatus().then(setRegistration);
  }, []);

  useEffect(() => {
    refresh();
    const subscription = AppState.addEventListener('change', (value) => value === 'active' && refresh());
    return () => subscription.remove();
  }, [refresh]);

  const register = async (requestPermission: boolean) => {
    setRegistering(true);
    try {
      const result = await registerForPushNotifications(requestPermission);
      setPermission(result.state);
      const status = await getPushDeviceRegistrationStatus();
      setRegistration(status);
      if (!result.registered && result.state === 'granted') {
        Alert.alert('Registration incomplete', 'QuickQueue could not register this device. Check your connection and try again.');
      } else if (result.state === 'unavailable') {
        Alert.alert('Notifications unavailable', 'Use a physical device and a development or production build.');
      }
    } finally {
      setRegistering(false);
    }
  };

  const enable = () => Alert.alert(
    'Allow QuickQueue notifications?',
    'Receive appointment, check-in, and queue updates. Notification previews avoid unnecessary personal information.',
    [
      { text: 'Not Now', style: 'cancel' },
      { text: 'Continue', onPress: () => { void register(true); } },
    ],
  );

  const permissionGranted = permission === 'granted';
  const permissionLabel = permissionGranted
    ? 'Enabled'
    : permission === 'denied'
      ? 'Blocked in device settings'
      : permission === 'unavailable'
        ? 'Unavailable on this build/device'
        : 'Not enabled';
  const registrationLabel = registration.state === 'registered'
    ? 'Registered with QuickQueue'
    : registration.state === 'not_registered'
      ? 'Not registered with QuickQueue'
      : 'Registration status unavailable';

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]}>
    <View style={[s.header, { backgroundColor: colors.primary }]}>
      <Pressable onPress={() => router.back()}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable>
      <Text style={s.heading}>Push Notifications</Text>
    </View>
    <View style={s.body}>
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Ionicons name={permissionGranted ? 'notifications' : 'notifications-off-outline'} size={32} color={permissionGranted ? '#159447' : colors.muted} />
        <Text style={[s.title, { color: colors.text }]}>Android notification permission</Text>
        <Text style={[s.status, { color: permissionGranted ? '#159447' : '#C45B00' }]}>{permissionLabel}</Text>
        <Text style={[s.copy, { color: colors.muted }]}>Permission allows QuickQueue notifications to appear on this device. Device Silent Mode and Do Not Disturb settings are also respected.</Text>
        {!permissionGranted && <Pressable onPress={permission === 'denied' ? openNotificationSettings : enable} style={s.button}>
          <Text style={s.buttonText}>{permission === 'denied' ? 'Open Device Settings' : 'Enable Notifications'}</Text>
        </Pressable>}

        <Text style={[s.title, { color: colors.text, marginTop: 18 }]}>QuickQueue device registration</Text>
        <Text style={[s.status, { color: registration.state === 'registered' ? '#159447' : '#C45B00' }]}>{registrationLabel}</Text>
        <Text style={[s.copy, { color: colors.muted }]}>This checks whether your account has an active registered device. It does not confirm that this device received a notification.</Text>
        <Pressable disabled={!permissionGranted || registering} onPress={() => { void register(false); }} style={[s.button, (!permissionGranted || registering) && { opacity: 0.55 }]}>
          <Text style={s.buttonText}>{registering ? 'Registering…' : registration.registered ? 'Retry Registration' : 'Register Device'}</Text>
        </Pressable>
      </View>
    </View>
  </SafeAreaView>;
}

const s = StyleSheet.create({
  safe: { flex: 1 },
  header: { alignItems: 'center', flexDirection: 'row', gap: 14, minHeight: 82, paddingHorizontal: 18 },
  heading: { color: '#FFF', fontSize: 20, fontWeight: '800' },
  body: { padding: 16 },
  card: { alignItems: 'center', borderRadius: 16, borderWidth: 1, padding: 12 },
  title: { fontSize: 14, fontWeight: '600', marginTop: 6 },
  status: { fontSize: 10, fontWeight: '500', marginTop: 2 },
  copy: { fontSize: 10, lineHeight: 16, marginTop: 8, textAlign: 'center' },
  button: { backgroundColor: '#0873FF', borderRadius: 9, marginTop: 12, minHeight: 38, paddingHorizontal: 17, paddingVertical: 8 },
  buttonText: { color: '#FFF', fontSize: 10, fontWeight: '600' },
});
