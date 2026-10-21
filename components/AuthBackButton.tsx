import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export function AuthBackButton({ onPress }: { onPress: () => void }) {
  const insets = useSafeAreaInsets();
  return <Pressable accessibilityLabel="Back to saved profile" accessibilityRole="button" hitSlop={6} onPress={onPress} style={[s.button, { top: insets.top + 10 }]}>
    <Ionicons name="chevron-back" size={26} color="#0646A8" />
  </Pressable>;
}

const s = StyleSheet.create({
  button: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, borderWidth: 0, elevation: 4, height: 44, justifyContent: 'center', left: 16, position: 'absolute', shadowColor: '#002B70', shadowOffset: { height: 2, width: 0 }, shadowOpacity: 0.16, shadowRadius: 5, width: 44, zIndex: 10 },
});
