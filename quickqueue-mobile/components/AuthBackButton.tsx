import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet } from 'react-native';

export function AuthBackButton({ onPress }: { onPress: () => void }) {
  return <Pressable accessibilityLabel="Back to saved profile" accessibilityRole="button" hitSlop={6} onPress={onPress} style={s.button}>
    <Ionicons name="chevron-back" size={26} color="#0646A8" />
  </Pressable>;
}

const s = StyleSheet.create({
  button: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#D8E6FA', borderRadius: 22, borderWidth: 1, elevation: 4, height: 44, justifyContent: 'center', left: 16, position: 'absolute', shadowColor: '#002B70', shadowOffset: { height: 2, width: 0 }, shadowOpacity: 0.18, shadowRadius: 4, top: 12, width: 44, zIndex: 10 },
});
