import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function Index() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [requiresPassword, setRequiresPassword] = useState(false);
  useEffect(() => { Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), AsyncStorage.getItem('quickqueue.requiresInitialPassword')]).then(([token, required]) => { setRequiresPassword(required === 'true'); setHasSession(Boolean(token)); }); }, []);
  if (hasSession === null) return <SafeAreaView style={{ flex: 1 }}><View style={{ alignItems: 'center', flex: 1, justifyContent: 'center' }}><ActivityIndicator color="#0346A8" /></View></SafeAreaView>;
  return <Redirect href={hasSession ? (requiresPassword ? '/set-password' : '/(tabs)') : '/login'} />;
}
