import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Href } from 'expo-router';
import { Linking, Platform } from 'react-native';

import { api } from '@/services/api';

const TOKEN_KEY = 'quickqueue.expoPushToken';
export const PENDING_ROUTE_KEY = 'quickqueue.pendingNotificationRoute';

export type PushPermissionState = 'granted' | 'denied' | 'undetermined' | 'unavailable';

export const configureNotificationChannels = async () => {
  if (Platform.OS !== 'android') return;
  await Promise.all([
    Notifications.setNotificationChannelAsync('appointment-updates', {
      name: 'Appointment updates',
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 200],
    }),
    Notifications.setNotificationChannelAsync('queue-alerts', {
      name: 'Queue alerts',
      description: 'Time-sensitive check-in and queue updates.',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 150, 250],
    }),
  ]);
};

export const getPushPermissionState = async (): Promise<PushPermissionState> => {
  if (!Device.isDevice || Platform.OS === 'web') return 'unavailable';
  const permission = await Notifications.getPermissionsAsync();
  return permission.granted ? 'granted' : permission.canAskAgain ? 'undetermined' : 'denied';
};

const uploadToken = async (token: string) => {
  const access = await AsyncStorage.getItem('quickqueue.accessToken');
  if (!access) return false;
  await api.post('push-devices/', {
    token,
    platform: Platform.OS,
    device_name: Device.deviceName || Device.modelName || Platform.OS,
  }, { headers: { Authorization: `Bearer ${access}` } });
  await AsyncStorage.setItem(TOKEN_KEY, token);
  return true;
};

export const registerForPushNotifications = async (requestPermission = false) => {
  if (!Device.isDevice || Platform.OS === 'web') return { state: 'unavailable' as const };
  await configureNotificationChannels();
  let permission = await Notifications.getPermissionsAsync();
  if (!permission.granted && requestPermission && permission.canAskAgain) {
    permission = await Notifications.requestPermissionsAsync();
  }
  if (!permission.granted) return { state: permission.canAskAgain ? 'undetermined' as const : 'denied' as const };

  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId ?? process.env.EXPO_PUBLIC_EAS_PROJECT_ID;
  if (!projectId) return { state: 'unavailable' as const, message: 'EAS project ID is not configured.' };
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  await uploadToken(token);
  return { state: 'granted' as const };
};

export const unregisterCurrentPushDevice = async () => {
  const [token, access] = await Promise.all([AsyncStorage.getItem(TOKEN_KEY), AsyncStorage.getItem('quickqueue.accessToken')]);
  if (token && access) {
    try {
      await api.delete('push-devices/', { data: { token }, headers: { Authorization: `Bearer ${access}` } });
    } catch { /* Logging out must still work offline; a later account registration reassigns the token safely. */ }
  }
  await AsyncStorage.removeItem(TOKEN_KEY);
};

export const notificationRoute = (data: Record<string, unknown>): Href => {
  if (data.type === 'QU') return '/(tabs)/queue';
  if (data.type === 'CO') return '/(tabs)/transactions';
  return '/(tabs)/transactions';
};

export const openNotificationSettings = () => Linking.openSettings();

export const syncChangedPushToken = (token: string) => uploadToken(token);
