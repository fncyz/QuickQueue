import AsyncStorage from '@react-native-async-storage/async-storage';
import { router, usePathname } from 'expo-router';
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Modal, Pressable, ScrollView, StyleSheet, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';

import { Text } from '@/components/Typography';
import { useAppTheme } from '@/contexts/app-theme';
import { getCurrentAccountId } from '@/services/offline-cache';

export type TutorialTargetId = 'home' | 'booking' | 'queue' | 'transactions' | 'specialServices' | 'notifications' | 'profile';
type TargetNode = { measureInWindow: (callback: (x: number, y: number, width: number, height: number) => void) => void };
type TargetRegistration = { node: TargetNode; reveal?: () => void };
type TargetRect = { height: number; left: number; top: number; width: number };
type ArrowGeometry = { headPath: string; path: string };

type TutorialContextValue = {
  isTutorialActive: boolean;
  registerTarget: (id: TutorialTargetId, node: TargetNode | null, options?: { reveal?: () => void }) => void;
  replayTutorial: () => void;
};

const TutorialContext = createContext<TutorialContextValue>({ isTutorialActive: false, registerTarget: () => undefined, replayTutorial: () => undefined });

const steps: { description: string; target?: TutorialTargetId; title: string }[] = [
  { title: 'Welcome to QuickQueue!', description: "Let's take a quick tour to help you get started with booking barangay appointments." },
  { target: 'home', title: 'Your Home Dashboard', description: 'View your upcoming appointments, available services, and important barangay updates here.' },
  { target: 'booking', title: 'Book an Appointment', description: 'Tap here to schedule a barangay service by selecting a service, date, and available time slot.' },
  { target: 'queue', title: 'Track Your Queue', description: 'Check your queue status and stay updated on your appointment progress.' },
  { target: 'transactions', title: 'Your Transactions', description: 'View your appointment history, booking status, and document transactions.' },
  { target: 'specialServices', title: 'Special Services & Events', description: 'Discover and book available barangay programs, community events, and temporary services.' },
  { target: 'notifications', title: 'Stay Updated', description: 'Receive updates about your appointments, successful bookings, and documents ready for pickup.' },
  { target: 'profile', title: 'Manage Your Profile', description: 'Update your personal information, manage security settings, and customize your app preferences.' },
  { title: "You're All Set!", description: "You're ready to explore QuickQueue and manage your barangay appointments with ease." },
];

const tutorialKey = (accountId: string) => `quickqueue.tutorial.${accountId.trim().toLowerCase()}`;
const isHomePath = (pathname: string) => pathname === '/' || pathname === '/(tabs)' || pathname === '/(tabs)/index';

export function TutorialProvider({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const targets = useRef(new Map<TutorialTargetId, TargetRegistration>());
  const checkedAccount = useRef<string | null>(null);
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [accountId, setAccountId] = useState<string | null>(null);

  const registerTarget = useCallback((id: TutorialTargetId, node: TargetNode | null, options?: { reveal?: () => void }) => {
    if (node) targets.current.set(id, { node, reveal: options?.reveal });
    else targets.current.delete(id);
  }, []);

  const begin = useCallback(async () => {
    const currentAccount = await getCurrentAccountId();
    if (!currentAccount) return;
    setAccountId(currentAccount);
    await AsyncStorage.setItem(tutorialKey(currentAccount), 'in-progress');
    setStepIndex(0);
    setActive(true);
  }, []);

  const replayTutorial = useCallback(() => {
    router.replace('/(tabs)');
    setTimeout(() => { void begin(); }, 350);
  }, [begin]);

  useEffect(() => {
    if (!isHomePath(pathname)) return;
    let cancelled = false;
    const check = async () => {
      const currentAccount = await getCurrentAccountId();
      if (!currentAccount || checkedAccount.current === currentAccount) return;
      checkedAccount.current = currentAccount;
      const status = await AsyncStorage.getItem(tutorialKey(currentAccount));
      if (!cancelled && status !== 'completed' && status !== 'skipped') {
        setAccountId(currentAccount);
        setTimeout(() => { if (!cancelled) { setStepIndex(0); setActive(true); } }, 500);
      }
    };
    void check();
    return () => { cancelled = true; };
  }, [pathname]);

  const finish = useCallback(async (status: 'completed' | 'skipped') => {
    setActive(false);
    if (accountId) await AsyncStorage.setItem(tutorialKey(accountId), status);
  }, [accountId]);

  const value = useMemo(() => ({ isTutorialActive: active, registerTarget, replayTutorial }), [active, registerTarget, replayTutorial]);
  return <TutorialContext.Provider value={value}>
    {children}
    <TutorialOverlay active={active} finish={finish} setStepIndex={setStepIndex} stepIndex={stepIndex} targets={targets} />
  </TutorialContext.Provider>;
}

function TutorialOverlay({ active, finish, setStepIndex, stepIndex, targets }: { active: boolean; finish: (status: 'completed' | 'skipped') => Promise<void>; setStepIndex: React.Dispatch<React.SetStateAction<number>>; stepIndex: number; targets: React.MutableRefObject<Map<TutorialTargetId, TargetRegistration>> }) {
  const { colors } = useAppTheme();
  const insets = useSafeAreaInsets();
  const { height: screenHeight, width: screenWidth } = useWindowDimensions();
  const [rect, setRect] = useState<TargetRect | null>(null);
  const [cardHeight, setCardHeight] = useState(0);
  const opacity = useRef(new Animated.Value(0)).current;
  const measurementGeneration = useRef(0);
  const step = steps[stepIndex];

  useEffect(() => {
    if (!active) return;
    const generation = ++measurementGeneration.current;
    const timers: ReturnType<typeof setTimeout>[] = [];
    setRect(null);
    opacity.setValue(0);
    if (!step.target) {
      Animated.timing(opacity, { duration: 220, toValue: 1, useNativeDriver: true }).start();
      return () => { measurementGeneration.current += 1; };
    }

    const measureAttempt = (attempt: number) => {
      if (generation !== measurementGeneration.current) return;
      const registration = targets.current.get(step.target!);
      if (!registration) {
        if (attempt < 12) timers.push(setTimeout(() => measureAttempt(attempt + 1), 100));
        else setStepIndex((current) => Math.min(current + 1, steps.length - 1));
        return;
      }
      if (attempt === 0) registration.reveal?.();
      registration.node.measureInWindow((x, y, width, height) => {
        if (generation !== measurementGeneration.current) return;
        const valid = Number.isFinite(x) && Number.isFinite(y) && width > 0 && height > 0 && x + width > 0 && y + height > 0 && x < screenWidth && y < screenHeight;
        if (!valid) {
          if (attempt < 12) timers.push(setTimeout(() => measureAttempt(attempt + 1), 100));
          else setStepIndex((current) => Math.min(current + 1, steps.length - 1));
          return;
        }
        const padding = 6;
        const left = Math.max(4, x - padding);
        const top = Math.max(4, y - padding);
        const right = Math.min(screenWidth - 4, x + width + padding);
        const bottom = Math.min(screenHeight - 4, y + height + padding);
        setRect({ height: bottom - top, left, top, width: right - left });
        Animated.timing(opacity, { duration: 220, toValue: 1, useNativeDriver: true }).start();
      });
    };
    timers.push(setTimeout(() => measureAttempt(0), step.target === 'specialServices' ? 400 : 60));
    return () => { measurementGeneration.current += 1; timers.forEach(clearTimeout); };
  }, [active, opacity, screenHeight, screenWidth, setStepIndex, step.target, targets]);

  if (!active) return null;
  const safeTop = insets.top + 12;
  const safeBottom = screenHeight - insets.bottom - 12;
  const measuredCardHeight = cardHeight || Math.min(260, safeBottom - safeTop);
  const bottomTarget = step.target === 'home' || step.target === 'booking' || step.target === 'queue' || step.target === 'transactions' || step.target === 'profile';
  const headerTarget = step.target === 'notifications';
  const centeredTop = Math.max(safeTop, Math.min(safeBottom - measuredCardHeight, (screenHeight - measuredCardHeight) / 2));
  const cardTop = centeredTop;
  const cardWidth = Math.min(460, screenWidth - 36);
  const cardLeft = (screenWidth - cardWidth) / 2;
  const arrow = rect && step.target ? arrowGeometry(rect, cardTop, measuredCardHeight, bottomTarget, headerTarget, screenWidth) : null;

  return <Modal animationType="none" onRequestClose={() => void finish('skipped')} statusBarTranslucent transparent visible>
    <Animated.View style={[styles.overlay, { opacity }]}>
      <View style={[styles.shade, StyleSheet.absoluteFill]} />
      {arrow && <TutorialArrow geometry={arrow} height={screenHeight} width={screenWidth} />}
      <View onLayout={(event) => setCardHeight(event.nativeEvent.layout.height)} style={[styles.card, { backgroundColor: '#FFFFFF', borderColor: '#E1E9F4', left: cardLeft, maxHeight: safeBottom - safeTop, top: cardTop, width: cardWidth }]}>
        <ScrollView bounces={false} contentContainerStyle={styles.cardContent} showsVerticalScrollIndicator={false}>
        <View style={styles.progressRow}><Text style={[styles.progress, { color: colors.accent }]}>Step {stepIndex + 1} of {steps.length}</Text><Pressable accessibilityRole="button" onPress={() => void finish('skipped')} hitSlop={8}><Text style={[styles.skip, styles.cardMuted]}>Skip Tutorial</Text></Pressable></View>
        <Text style={[styles.title, styles.cardText]}>{step.title}</Text>
        <Text style={[styles.description, styles.cardMuted]}>{step.description}</Text>
        <View style={styles.dots}>{steps.map((_, index) => <View key={index} style={[styles.dot, { backgroundColor: index === stepIndex ? colors.accent : '#D9E4F4' }, index === stepIndex && styles.activeDot]} />)}</View>
        <View style={styles.actions}>
          {stepIndex > 0 && stepIndex < steps.length - 1 ? <Pressable accessibilityRole="button" onPress={() => setStepIndex((current) => current - 1)} style={[styles.back, { borderColor: '#E1E9F4' }]}><Text style={[styles.backText, styles.cardText]}>Back</Text></Pressable> : <View />}
          <Pressable accessibilityRole="button" onPress={() => stepIndex === steps.length - 1 ? void finish('completed') : setStepIndex((current) => current + 1)} style={styles.next}><Text style={styles.nextText}>{stepIndex === 0 ? 'Start Tutorial' : stepIndex === steps.length - 1 ? 'Get Started' : 'Next'}</Text></Pressable>
        </View>
        </ScrollView>
      </View>
    </Animated.View>
  </Modal>;
}

export const useTutorial = () => useContext(TutorialContext);

function arrowGeometry(rect: TargetRect, cardTop: number, cardHeight: number, bottomTarget: boolean, headerTarget: boolean, screenWidth: number): ArrowGeometry {
  const targetX = rect.left + rect.width / 2;
  const targetTop = rect.top - 9;
  const targetBottom = rect.top + rect.height + 9;
  const cardBottom = cardTop + cardHeight;
  const cardAbove = bottomTarget || (!headerTarget && cardBottom < rect.top);
  const startY = cardAbove ? cardBottom + 8 : cardTop - 8;
  const endY = cardAbove ? targetTop : targetBottom;
  const startX = Math.max(28, Math.min(targetX + (targetX < screenWidth / 2 ? 24 : -24), screenWidth - 28));
  const controlX = targetX + (startX <= targetX ? -18 : 18);
  const controlY = (startY + endY) / 2;
  const angle = Math.atan2(endY - controlY, targetX - controlX);
  const headLength = 11;
  const spread = 0.62;
  const headOneX = targetX - headLength * Math.cos(angle - spread);
  const headOneY = endY - headLength * Math.sin(angle - spread);
  const headTwoX = targetX - headLength * Math.cos(angle + spread);
  const headTwoY = endY - headLength * Math.sin(angle + spread);
  return {
    headPath: `M${headOneX} ${headOneY}L${targetX} ${endY}L${headTwoX} ${headTwoY}`,
    path: `M${startX} ${startY} Q${controlX} ${controlY} ${targetX} ${endY}`,
  };
}

function TutorialArrow({ geometry, height, width }: { geometry: ArrowGeometry; height: number; width: number }) {
  return <Svg height={height} pointerEvents="none" style={StyleSheet.absoluteFill} width={width}>
    <Path d={geometry.path} fill="none" stroke="#60A5FA" strokeDasharray="8 7" strokeLinecap="round" strokeWidth={2.75} />
    <Path d={geometry.headPath} fill="none" stroke="#60A5FA" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.75} />
  </Svg>;
}

const styles = StyleSheet.create({
  overlay: { flex: 1 },
  shade: { backgroundColor: 'rgba(3, 12, 28, 0.72)', position: 'absolute' },
  card: { borderRadius: 20, borderWidth: 1, elevation: 10, overflow: 'hidden', position: 'absolute', shadowColor: '#001A47', shadowOffset: { height: 5, width: 0 }, shadowOpacity: 0.24, shadowRadius: 12 },
  cardContent: { padding: 18 },
  cardText: { color: '#10295E' }, cardMuted: { color: '#718098' },
  progressRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  progress: { fontSize: 11, fontWeight: '700' }, skip: { fontSize: 11, fontWeight: '600' },
  title: { fontSize: 20, fontWeight: '800', marginTop: 16 }, description: { fontSize: 13, lineHeight: 20, marginTop: 8 },
  dots: { alignItems: 'center', flexDirection: 'row', gap: 5, marginTop: 18 }, dot: { borderRadius: 4, height: 7, width: 7 }, activeDot: { width: 18 },
  actions: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 18 },
  back: { alignItems: 'center', borderRadius: 12, borderWidth: 1, justifyContent: 'center', minHeight: 44, paddingHorizontal: 20 }, backText: { fontSize: 13, fontWeight: '700' },
  next: { alignItems: 'center', backgroundColor: '#0759D9', borderRadius: 12, justifyContent: 'center', minHeight: 44, paddingHorizontal: 22 }, nextText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },
});
