import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';

import { Text } from '@/components/Typography';
import { useConnectivity } from '@/contexts/connectivity';

export function SavedInformationBanner({ message = 'Saved Information · Statuses may not be up to Date.', followedByOverlap = true }: { message?: string; followedByOverlap?: boolean }) {
  const { isOnline } = useConnectivity();
  if (isOnline) return null;

  return <View style={[s.banner, followedByOverlap && s.beforeOverlap]}>
    <Ionicons name="cloud-offline-outline" size={20} color="#DC2626" />
    <Text style={s.text}>{message}</Text>
  </View>;
}

const s = StyleSheet.create({
  banner: { alignItems: 'center', backgroundColor: '#FEF2F2', borderColor: '#FECACA', borderRadius: 20, borderWidth: 1, flexDirection: 'row', gap: 11, marginBottom: 18, marginHorizontal: 18, marginTop: -26, minHeight: 64, paddingHorizontal: 17, paddingVertical: 12 },
  beforeOverlap: { marginBottom: 42 },
  text: { color: '#B91C1C', flex: 1, flexShrink: 1, fontSize: 10, fontWeight: '800', lineHeight: 15 },
});
