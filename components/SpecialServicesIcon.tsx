import { MaterialCommunityIcons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/contexts/app-theme';

export function SpecialServicesIcon({ size = 24 }: { size?: number }) {
  const { colors } = useAppTheme();
  return <View style={[s.icon, { backgroundColor: colors.accent, borderRadius: size / 2, height: size, width: size }]}><MaterialCommunityIcons name="hand-heart" size={size * 0.7} color="#FFF" /></View>;
}

const s = StyleSheet.create({
  icon: { alignItems: 'center', justifyContent: 'center' },
});
