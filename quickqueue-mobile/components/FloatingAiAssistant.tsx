import { Image, Pressable, StyleSheet, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const assistantLogo = require('../assets/images/qq-ai.png');
const assistantBlue = '#21498B';

export function FloatingAiAssistant() {
  const { width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const size = Math.max(56, Math.min(62, width * 0.15));

  return <Pressable
    accessibilityHint="AI assistant features are coming soon"
    accessibilityLabel="QuickQueue AI assistant"
    accessibilityRole="button"
    onPress={() => undefined}
    style={({ pressed }) => [
      styles.button,
      {
        backgroundColor: assistantBlue,
        borderColor: assistantBlue,
        bottom: insets.bottom + 101,
        height: size,
        opacity: pressed ? 0.82 : 1,
        right: Math.max(18, width * 0.045),
        transform: [{ scale: pressed ? 0.96 : 1 }],
        width: size,
      },
    ]}
  >
    <Image source={assistantLogo} resizeMode="contain" style={[styles.logo, { height: size - 10, width: size - 10 }]} />
  </Pressable>;
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: 2,
    elevation: 7,
    justifyContent: 'center',
    overflow: 'hidden',
    position: 'absolute',
    shadowColor: '#082F76',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.22,
    shadowRadius: 7,
    zIndex: 20,
  },
  logo: { borderRadius: 999 },
});
