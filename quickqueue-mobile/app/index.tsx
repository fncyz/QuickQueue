import AsyncStorage from '@react-native-async-storage/async-storage';
import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { securitySetupRoute } from '@/services/security-flow';
import { readRecentResidentProfile } from '@/services/offline-cache';
import { QuickQueueLoadingScreen } from '@/components/QuickQueueLoadingScreen';
import { waitForStartupLoadingWindow } from '@/services/startup-loading';

export default function Index() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [hasRecentProfile, setHasRecentProfile] = useState(false);
  const [explicitlyLoggedOut, setExplicitlyLoggedOut] = useState(false);
  const [destination, setDestination] = useState<ReturnType<typeof securitySetupRoute>>('/(tabs)');
  useEffect(() => {
    let active = true;
    Promise.all([
      Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), AsyncStorage.getItem('quickqueue.securitySetupStage'), AsyncStorage.getItem('quickqueue.pendingUsername'), AsyncStorage.getItem('quickqueue.explicitLogout'), readRecentResidentProfile()]),
      waitForStartupLoadingWindow(),
    ])
      .then(([[token, stage, pending, loggedOut, recentProfile]]) => {
        if (!active) return;
        setDestination(securitySetupRoute(stage, Boolean(pending)));
        setHasRecentProfile(Boolean(recentProfile));
        setExplicitlyLoggedOut(loggedOut === 'true');
        setHasSession(Boolean(token));
      })
      .catch(() => {
        if (!active) return;
        setExplicitlyLoggedOut(true);
        setHasSession(false);
      });
    return () => { active = false; };
  }, []);
  if (hasSession === null) return <QuickQueueLoadingScreen />;
  if (explicitlyLoggedOut) return <Redirect href="/login" />;
  if (hasSession && destination !== '/(tabs)') return <Redirect href={destination} />;
  return <Redirect href={hasRecentProfile ? '/welcome-back' : '/login'} />;
}
