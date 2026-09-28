import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { securitySetupRoute } from '@/services/security-flow';
import { readRecentResidentProfile } from '@/services/offline-cache';

export default function Index() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [hasRecentProfile, setHasRecentProfile] = useState(false);
  const [destination, setDestination] = useState<ReturnType<typeof securitySetupRoute>>('/(tabs)');
  useEffect(() => { Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), AsyncStorage.getItem('quickqueue.securitySetupStage'), AsyncStorage.getItem('quickqueue.pendingUsername'), readRecentResidentProfile()]).then(([token, stage, pending, recentProfile]) => { setDestination(securitySetupRoute(stage, Boolean(pending))); setHasRecentProfile(Boolean(recentProfile)); setHasSession(Boolean(token)); }); }, []);
  if (hasSession === null) return <SafeAreaView style={{ flex: 1 }}><View style={{ alignItems: 'center', flex: 1, justifyContent: 'center' }}><ActivityIndicator color="#0346A8" /></View></SafeAreaView>;
  return <Redirect href={hasSession ? destination : hasRecentProfile ? '/welcome-back' : '/login'} />;
}
