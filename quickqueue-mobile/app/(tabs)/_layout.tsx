import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect, Tabs } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ResidentTabBar } from '@/components/ResidentTabBar';

export default function TabLayout() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [hasSession, setHasSession] = useState(false);
  const [requiresPassword, setRequiresPassword] = useState(false);

  useEffect(() => {
    Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), AsyncStorage.getItem('quickqueue.requiresInitialPassword')])
      .then(([token, required]) => { setHasSession(Boolean(token)); setRequiresPassword(required === 'true'); })
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) return <SafeAreaView style={{ flex: 1 }}><View style={{ alignItems: 'center', flex: 1, justifyContent: 'center' }}><ActivityIndicator color="#0346A8" /></View></SafeAreaView>;
  if (!hasSession) return <Redirect href="/login" />;
  if (requiresPassword) return <Redirect href="/set-password" />;

  return <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <ResidentTabBar {...props} />}>
    <Tabs.Screen name="index" options={{ title: 'Home' }} />
    <Tabs.Screen name="queue" options={{ title: 'Queue' }} />
    <Tabs.Screen name="booking" options={{ title: 'Book' }} />
    <Tabs.Screen name="transactions" options={{ title: 'Transactions' }} />
    <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
    <Tabs.Screen name="explore" options={{ href: null }} />
  </Tabs>;
}
