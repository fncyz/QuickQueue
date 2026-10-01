import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { PropsWithChildren, useEffect } from 'react';

import { useAuthSession } from '@/contexts/auth-session';
import { notificationRoute, PENDING_ROUTE_KEY, registerForPushNotifications, syncChangedPushToken } from '@/services/push-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldPlaySound: true, shouldSetBadge: false, shouldShowBanner: true, shouldShowList: true }),
});

export function PushNotificationsProvider({ children }: PropsWithChildren) {
  const { isUnlocked } = useAuthSession();

  useEffect(() => {
    registerForPushNotifications(false).catch(() => undefined);
    const tokenSubscription = Notifications.addPushTokenListener(({ data }) => { syncChangedPushToken(data).catch(() => undefined); });
    const responseSubscription = Notifications.addNotificationResponseReceivedListener(async (response) => {
      const target = notificationRoute(response.notification.request.content.data);
      if (isUnlocked) router.push(target);
      else {
        await AsyncStorage.setItem(PENDING_ROUTE_KEY, String(target));
        router.push('/welcome-back');
      }
    });
    Notifications.getLastNotificationResponseAsync().then(async (response) => {
      if (!response) return;
      const target = notificationRoute(response.notification.request.content.data);
      if (isUnlocked) router.push(target);
      else await AsyncStorage.setItem(PENDING_ROUTE_KEY, String(target));
      await Notifications.clearLastNotificationResponseAsync();
    }).catch(() => undefined);
    return () => { tokenSubscription.remove(); responseSubscription.remove(); };
  }, [isUnlocked]);

  useEffect(() => {
    if (!isUnlocked) return;
    AsyncStorage.getItem(PENDING_ROUTE_KEY).then(async (target) => {
      if (!target) return;
      await AsyncStorage.removeItem(PENDING_ROUTE_KEY);
      router.push(target as never);
    });
  }, [isUnlocked]);

  return children;
}
