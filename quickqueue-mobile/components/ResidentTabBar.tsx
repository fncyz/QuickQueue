import { Ionicons } from '@expo/vector-icons';
import { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAppTheme } from '@/contexts/app-theme';
import { appTypography } from '@/constants/typography';
import { TutorialTargetId, useTutorial } from '@/contexts/tutorial';
import { useCallback } from 'react';

const items = {
  index: { label: 'Home', icon: 'home' as const, center: false },
  queue: { label: 'Queue', icon: 'people' as const, center: false },
  booking: { label: '', icon: 'add' as const, center: true },
  transactions: { label: 'Transactions', icon: 'document-text' as const, center: false },
  profile: { label: 'Profile', icon: 'person-outline' as const, center: false },
};

/** Persistent resident navigation, deliberately kept separate from screen content. */
export function ResidentTabBar({ state, navigation }: BottomTabBarProps) {
  const { colors } = useAppTheme();
  return <SafeAreaView edges={['bottom']} style={[styles.safeArea, { backgroundColor: colors.background }]}><View style={[styles.bar, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    {state.routes.map((route, index) => {
      const item = items[route.name as keyof typeof items];
      if (!item) return null;

      const focused = state.index === index;
      const tutorialTarget = route.name === 'index' ? 'home' : route.name === 'booking' ? 'booking' : route.name === 'queue' ? 'queue' : route.name === 'transactions' ? 'transactions' : route.name === 'profile' ? 'profile' : null;
      return <ResidentTabItem colors={colors} focused={focused} item={item} key={route.key} onPress={() => !focused && navigation.navigate(route.name)} tutorialTarget={tutorialTarget} />;
    })}
  </View></SafeAreaView>;
}

function ResidentTabItem({ colors, focused, item, onPress, tutorialTarget }: { colors: ReturnType<typeof useAppTheme>['colors']; focused: boolean; item: (typeof items)[keyof typeof items]; onPress: () => void; tutorialTarget: TutorialTargetId | null }) {
  const { registerTarget } = useTutorial();
  const itemTarget = useCallback((node: View | null) => {
    if (tutorialTarget && tutorialTarget !== 'booking') registerTarget(tutorialTarget, node);
  }, [registerTarget, tutorialTarget]);
  const bookingTarget = useCallback((node: View | null) => {
    if (tutorialTarget === 'booking') registerTarget('booking', node);
  }, [registerTarget, tutorialTarget]);

  return <Pressable onPress={onPress} style={[styles.item, item.center && styles.centerItem]} accessibilityRole="button" accessibilityState={focused ? { selected: true } : {}}>
    {item.center
      ? <View ref={bookingTarget} collapsable={false} style={[styles.iconWrap, styles.centerIcon]}><Ionicons name={item.icon} size={36} color="#FFFFFF" /></View>
      : <View style={styles.targetContent}><View ref={itemTarget} collapsable={false} style={styles.iconWrap}><Ionicons name={item.icon} size={24} color={focused ? colors.accent : colors.muted} /></View><Text fixedFontSize={8} numberOfLines={1} style={[styles.label, { color: focused ? colors.accent : colors.muted }, focused && styles.labelActive]}>{item.label}</Text></View>}
  </Pressable>;
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: '#FFFFFF', paddingHorizontal: 10, paddingTop: 13 },
  bar: { alignItems: 'flex-end', backgroundColor: '#FFFFFF', borderColor: '#E4E9F1', borderRadius: 36, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', height: 72, paddingHorizontal: 6, shadowColor: '#173B78', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.035, shadowRadius: 5, elevation: 1 },
  item: { alignItems: 'center', flex: 1, gap: 4, height: 67, justifyContent: 'center', paddingHorizontal: 1 },
  centerItem: { height: 90 },
  iconWrap: { alignItems: 'center', height: 28, justifyContent: 'center', width: 36 },
  centerIcon: { backgroundColor: '#0639B7', borderRadius: 37, height: 74, shadowColor: '#0A2D82', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 4, elevation: 2, width: 74 },
  targetContent: { alignItems: 'center', gap: 4 },
  label: { ...appTypography.tabLabel, color: '#344158', fontSize: 8, lineHeight: 11 },
  labelActive: { color: '#073CB5', fontWeight: '800' },
  centerLabel: { color: '#073CB5', fontWeight: '800' },
});
