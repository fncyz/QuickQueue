import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect, Tabs, usePathname } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ResidentTabBar } from '@/components/ResidentTabBar';
import { FloatingAiAssistant } from '@/components/FloatingAiAssistant';
import { ConnectionStatusBanner, useConnectivity } from '@/contexts/connectivity';
import { useAssistantPreference } from '@/contexts/assistant-preference';
import { securitySetupRoute } from '@/services/security-flow';

export default function TabLayout() {
  const { notice } = useConnectivity();
  const { enabled: assistantEnabled } = useAssistantPreference();
  const pathname = usePathname();
  const [checkingSession, setCheckingSession] = useState(true);
  const [hasSession, setHasSession] = useState(false);
  const [setupStage, setSetupStage] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), AsyncStorage.getItem('quickqueue.securitySetupStage')])
      .then(([token, stage]) => { setHasSession(Boolean(token)); setSetupStage(stage); })
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) return <SafeAreaView style={{ flex: 1 }}><View style={{ alignItems: 'center', flex: 1, justifyContent: 'center' }}><ActivityIndicator color="#0346A8" /></View></SafeAreaView>;
  if (!hasSession) return <Redirect href="/login" />;
  if (setupStage && setupStage !== 'complete') return <Redirect href={securitySetupRoute(setupStage)} />;

  return <View style={{ flex: 1 }}>
    <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <ResidentTabBar {...props} />}> 
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="queue" options={{ title: 'Queue' }} />
      <Tabs.Screen name="booking" options={{ title: 'Book' }} />
      <Tabs.Screen name="transactions" options={{ title: 'Transactions' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
      <Tabs.Screen name="explore" options={{ href: null }} />
    </Tabs>
    {(assistantEnabled || pathname === '/' || pathname === '/(tabs)' || pathname === '/(tabs)/index') && <FloatingAiAssistant />}
    {notice && <ConnectionStatusBanner />}
  </View>;
}
