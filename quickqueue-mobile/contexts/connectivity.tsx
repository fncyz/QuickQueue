import NetInfo from '@react-native-community/netinfo';
import { Ionicons } from '@expo/vector-icons';
import { createContext, PropsWithChildren, useContext, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Text } from '@/components/Typography';

type ConnectionNotice = 'offline' | 'backOnline' | null;
type ConnectivityValue = { dismissNotice: () => void; isOnline: boolean; notice: ConnectionNotice; reconnectVersion: number };
const ConnectivityContext = createContext<ConnectivityValue>({ dismissNotice: () => undefined, isOnline: true, notice: null, reconnectVersion: 0 });

export function ConnectivityProvider({ children }: PropsWithChildren) {
  const [isOnline, setIsOnline] = useState(true);
  const [reconnectVersion, setReconnectVersion] = useState(0);
  const [notice, setNotice] = useState<ConnectionNotice>(null);
  const previousOnline = useRef<boolean | null>(null);

  useEffect(() => NetInfo.addEventListener((state) => {
    const online = Boolean(state.isConnected && state.isInternetReachable !== false);
    if (previousOnline.current === null) {
      if (!online) setNotice('offline');
    } else if (previousOnline.current === false && online) {
      setReconnectVersion((value) => value + 1);
      setNotice('backOnline');
    } else if (previousOnline.current === true && !online) {
      setNotice('offline');
    }
    previousOnline.current = online;
    setIsOnline(online);
  }), []);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 3000);
    return () => clearTimeout(timer);
  }, [notice]);

  return <ConnectivityContext.Provider value={{ dismissNotice: () => setNotice(null), isOnline, notice, reconnectVersion }}>{children}</ConnectivityContext.Provider>;
}

export const useConnectivity = () => useContext(ConnectivityContext);

export function ConnectionStatusBanner() {
  const { dismissNotice, notice } = useConnectivity();
  if (!notice) return null;
  const onlineAgain = notice === 'backOnline';
  const palette = onlineAgain
    ? { background: '#083E32', border: '#259B65', icon: '#18B875', iconSoft: '#164E41' }
    : { background: '#6F1D1B', border: '#FF8174', icon: '#E33E32', iconSoft: '#842C28' };
  return <View accessibilityLiveRegion="polite" style={s.container}>
    <View style={[s.banner, { backgroundColor: palette.background, borderColor: palette.border }]}>
      <View style={[s.icon, { backgroundColor: palette.icon }]}><Ionicons name={onlineAgain ? 'wifi' : 'cloud-offline'} size={27} color="#FFFFFF" /></View>
      <View style={s.copy}><Text style={s.title}>{onlineAgain ? 'Back Online' : 'You’re Offline'}</Text><Text style={s.message}>{onlineAgain ? 'Refreshing your latest information.' : 'Some saved information ay not be up to date.'}</Text></View>
      <Pressable accessibilityLabel="Dismiss connection status" onPress={dismissNotice} style={[s.close, { backgroundColor: palette.iconSoft }]}><Ionicons name="close" size={24} color="#FFFFFF" /></Pressable>
    </View>
  </View>;
}

const s = StyleSheet.create({
  container: { paddingBottom: 8, paddingTop: 10 },
  banner: { alignItems: 'center', borderRadius: 18, borderWidth: 1.5, elevation: 4, flexDirection: 'row', gap: 12, marginHorizontal: 18, minHeight: 82, paddingHorizontal: 13, paddingVertical: 11, shadowColor: '#000', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.18, shadowRadius: 7 },
  icon: { alignItems: 'center', borderRadius: 30, height: 58, justifyContent: 'center', width: 58 },
  copy: { flex: 1 },
  title: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' },
  message: { color: '#E4F4EC', fontSize: 11, lineHeight: 16, marginTop: 3, opacity: 0.9 },
  close: { alignItems: 'center', borderRadius: 24, height: 46, justifyContent: 'center', width: 46 },
});
