import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Href } from 'expo-router';
import { Linking, Platform } from 'react-native';

import { api } from '@/services/api';
import { getCurrentAccountId } from '@/services/offline-cache';

const TOKEN_KEY = 'quickqueue.expoPushToken';
export const PENDING_ROUTE_KEY = 'quickqueue.pendingNotificationRoute';

export type PushPermissionState = 'granted' | 'denied' | 'undetermined' | 'unavailable';
export type PushRegistrationIssue =
  | 'authentication_required'
  | 'account_unavailable'
  | 'session_changed'
  | 'project_id_missing'
  | 'registration_failed';

export type PushRegistrationResult = {
  state: PushPermissionState;
  registered: boolean;
  issue?: PushRegistrationIssue;
};

export type PushDeviceRegistrationStatus = {
  state: 'registered' | 'not_registered' | 'unavailable';
  registered: boolean;
  issue?: 'authentication_required' | 'status_check_failed';
};

type PushUploadResult = Pick<PushRegistrationResult, 'registered' | 'issue'>;

const inFlightUploads = new Map<string, Promise<PushUploadResult>>();
const tokenQueues = new Map<string, Promise<void>>();
const registeredAccountByToken = new Map<string, string>();

const reportPushFailure = (stage: string, error: unknown, issue?: string) => {
  const details = error as { code?: unknown; response?: { status?: unknown } } | null;
  const status = typeof details?.response?.status === 'number' ? details.response.status : undefined;
  const code = typeof details?.code === 'string' && /^[A-Z0-9_-]{1,32}$/.test(details.code)
    ? details.code
    : undefined;

  // Never log exception messages, request config, tokens, or payloads.
  console.warn('QuickQueue push registration failed', { stage, issue, status, code });
};

const enqueueForToken = <T,>(token: string, task: () => Promise<T>): Promise<T> => {
  const previous = tokenQueues.get(token) ?? Promise.resolve();
  const queued = previous.catch(() => undefined).then(task);
  const tail = queued.then(() => undefined, () => undefined);
  tokenQueues.set(token, tail);
  void tail.then(() => {
    if (tokenQueues.get(token) === tail) tokenQueues.delete(token);
  });
  return queued;
};

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
  try {
    const permission = await Notifications.getPermissionsAsync();
    return permission.granted ? 'granted' : permission.canAskAgain ? 'undetermined' : 'denied';
  } catch (error) {
    reportPushFailure('permission_check', error);
    return 'unavailable';
  }
};

export const getPushDeviceRegistrationStatus = async (): Promise<PushDeviceRegistrationStatus> => {
  try {
    const access = await AsyncStorage.getItem('quickqueue.accessToken');
    if (!access) {
      return { state: 'unavailable', registered: false, issue: 'authentication_required' };
    }
    const response = await api.get<{ enabled?: boolean }>('push-devices/', {
      headers: { Authorization: `Bearer ${access}` },
    });
    const registered = response.data.enabled === true;
    return { state: registered ? 'registered' : 'not_registered', registered };
  } catch (error) {
    reportPushFailure('registration_status_check', error, 'status_check_failed');
    return { state: 'unavailable', registered: false, issue: 'status_check_failed' };
  }
};

const uploadToken = async (token: string): Promise<PushUploadResult> => {
  let access: string | null;
  let accountId: string | null;
  try {
    [access, accountId] = await Promise.all([
      AsyncStorage.getItem('quickqueue.accessToken'),
      getCurrentAccountId(),
    ]);
  } catch (error) {
    reportPushFailure('session_read', error, 'registration_failed');
    return { registered: false, issue: 'registration_failed' };
  }
  if (!access) {
    reportPushFailure('backend_registration', null, 'authentication_required');
    return { registered: false, issue: 'authentication_required' };
  }
  if (!accountId) {
    reportPushFailure('backend_registration', null, 'account_unavailable');
    return { registered: false, issue: 'account_unavailable' };
  }

  if (registeredAccountByToken.get(token) === accountId) {
    return { registered: true };
  }

  const inFlightKey = `${accountId}\u0000${token}`;
  const existing = inFlightUploads.get(inFlightKey);
  if (existing) return existing;

  const pending = enqueueForToken(token, async (): Promise<PushUploadResult> => {
    try {
      const [currentAccess, currentAccountId] = await Promise.all([
        AsyncStorage.getItem('quickqueue.accessToken'),
        getCurrentAccountId(),
      ]);
      if (!currentAccess || currentAccountId !== accountId) {
        return { registered: false, issue: 'session_changed' };
      }

      await api.post('push-devices/', {
        token,
        platform: Platform.OS,
        device_name: Device.deviceName || Device.modelName || Platform.OS,
      }, { headers: { Authorization: `Bearer ${currentAccess}` } });

      const latestAccountId = await getCurrentAccountId();
      if (latestAccountId !== accountId) {
        return { registered: false, issue: 'session_changed' };
      }

      await AsyncStorage.setItem(TOKEN_KEY, token);
      registeredAccountByToken.set(token, accountId);
      return { registered: true };
    } catch (error) {
      reportPushFailure('backend_registration', error, 'registration_failed');
      return { registered: false, issue: 'registration_failed' };
    }
  });

  inFlightUploads.set(inFlightKey, pending);
  void pending.then(() => {
    if (inFlightUploads.get(inFlightKey) === pending) inFlightUploads.delete(inFlightKey);
  });
  return pending;
};

export const registerForPushNotifications = async (requestPermission = false): Promise<PushRegistrationResult> => {
  if (!Device.isDevice || Platform.OS === 'web') {
    return { state: 'unavailable', registered: false };
  }

  try {
    await configureNotificationChannels();
    let permission = await Notifications.getPermissionsAsync();
    if (!permission.granted && requestPermission && permission.canAskAgain) {
      permission = await Notifications.requestPermissionsAsync();
    }
    if (!permission.granted) {
      return {
        state: permission.canAskAgain ? 'undetermined' : 'denied',
        registered: false,
      };
    }

    const projectId = Constants.expoConfig?.extra?.eas?.projectId
      ?? Constants.easConfig?.projectId
      ?? process.env.EXPO_PUBLIC_EAS_PROJECT_ID;
    if (!projectId) {
      reportPushFailure('expo_token', null, 'project_id_missing');
      return { state: 'unavailable', registered: false, issue: 'project_id_missing' };
    }

    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    const upload = await uploadToken(token);
    return { state: 'granted', ...upload };
  } catch (error) {
    reportPushFailure('expo_token', error, 'registration_failed');
    return { state: 'unavailable', registered: false, issue: 'registration_failed' };
  }
};

export const unregisterCurrentPushDevice = async () => {
  const [token, access, accountId] = await Promise.all([
    AsyncStorage.getItem(TOKEN_KEY),
    AsyncStorage.getItem('quickqueue.accessToken'),
    getCurrentAccountId(),
  ]);
  if (token && access) {
    try {
      await enqueueForToken(token, async () => {
        const [currentAccess, currentAccountId] = await Promise.all([
          AsyncStorage.getItem('quickqueue.accessToken'),
          getCurrentAccountId(),
        ]);
        if (currentAccess !== access || currentAccountId !== accountId) return;
        await api.delete('push-devices/', {
          data: { token },
          headers: { Authorization: `Bearer ${currentAccess}` },
        });
        if (accountId && registeredAccountByToken.get(token) === accountId) {
          registeredAccountByToken.delete(token);
        }
      });
    } catch (error) {
      reportPushFailure('backend_unregistration', error, 'registration_failed');
    }
  }
  await AsyncStorage.removeItem(TOKEN_KEY);
};

export const notificationRoute = (data: Record<string, unknown>): Href => {
  if (data.route === 'queue') return '/(tabs)/queue';
  if (data.route === 'transactions') return '/(tabs)/transactions';
  if (data.type === 'QU') return '/(tabs)/queue';
  if (['CO', 'DU', 'EV', 'AC', 'AR', 'CA'].includes(String(data.type))) return '/(tabs)/transactions';
  return '/(tabs)/transactions';
};

export const openNotificationSettings = () => Linking.openSettings();

export const syncChangedPushToken = async (token: string): Promise<PushRegistrationResult> => {
  const result = await uploadToken(token);
  return { state: 'granted', ...result };
};
