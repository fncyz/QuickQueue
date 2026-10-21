import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

const CONFETTI = [
  { color: '#FFC928', delay: 0, x: -0.92, drift: -18, rotate: '220deg', shape: 'strip' },
  { color: '#39CC91', delay: 45, x: -0.72, drift: 12, rotate: '150deg', shape: 'square' },
  { color: '#368CFF', delay: 90, x: -0.52, drift: -14, rotate: '250deg', shape: 'strip' },
  { color: '#FF6577', delay: 25, x: -0.32, drift: 18, rotate: '190deg', shape: 'square' },
  { color: '#9B6DFF', delay: 120, x: -0.12, drift: -10, rotate: '280deg', shape: 'strip' },
  { color: '#FFC928', delay: 60, x: 0.12, drift: 13, rotate: '210deg', shape: 'square' },
  { color: '#25BDE2', delay: 10, x: 0.34, drift: -12, rotate: '260deg', shape: 'strip' },
  { color: '#FF6577', delay: 105, x: 0.54, drift: 18, rotate: '170deg', shape: 'square' },
  { color: '#39CC91', delay: 35, x: 0.73, drift: -9, rotate: '240deg', shape: 'strip' },
  { color: '#368CFF', delay: 80, x: 0.91, drift: 15, rotate: '200deg', shape: 'square' },
] as const;

export function SuccessAnimation({ color = '#39CC91', size = 100 }: { color?: string; size?: number }) {
  const scale = useRef(new Animated.Value(0.35)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const halo = useRef(new Animated.Value(0.6)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(scale, { friction: 5, tension: 85, toValue: 1, useNativeDriver: true }),
      Animated.timing(opacity, { duration: 280, toValue: 1, useNativeDriver: true }),
      Animated.sequence([
        Animated.delay(180),
        Animated.spring(halo, { friction: 6, toValue: 1, useNativeDriver: true }),
      ]),
    ]).start();
  }, [halo, opacity, scale]);

  return <View pointerEvents="none" style={[s.stage, { height: size * 1.28, width: size * 2.45 }]}>
    {CONFETTI.map((piece, index) => <ConfettiPiece key={`${piece.color}-${index}`} {...piece} size={size} />)}
    <Animated.View style={[s.halo, { backgroundColor: `${color}24`, height: size, opacity, transform: [{ scale: halo }], width: size }]}>
      <Animated.View style={[s.seal, { backgroundColor: color, height: size * 0.68, transform: [{ scale }], width: size * 0.68 }]}>
        <Ionicons name="checkmark" size={size * 0.45} color="#FFFFFF" />
      </Animated.View>
    </Animated.View>
  </View>;
}

function ConfettiPiece({ color, delay, drift, rotate, shape, size, x }: (typeof CONFETTI)[number] & { size: number }) {
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.sequence([
      Animated.delay(delay),
      Animated.timing(progress, { duration: 1050, toValue: 1, useNativeDriver: true }),
    ]).start();
  }, [delay, progress]);
  const top = size * 0.08;
  return <Animated.View style={[s.confetti, shape === 'strip' ? s.confettiStrip : s.confettiSquare, {
    backgroundColor: color,
    left: size * 1.225 + x * size,
    opacity: progress.interpolate({ inputRange: [0, 0.1, 0.78, 1], outputRange: [0, 1, 1, 0] }),
    top,
    transform: [
      { translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [0, drift] }) },
      { translateY: progress.interpolate({ inputRange: [0, 0.32, 1], outputRange: [0, -size * 0.26, size * 0.72] }) },
      { rotate: progress.interpolate({ inputRange: [0, 1], outputRange: ['0deg', rotate] }) },
      { scale: progress.interpolate({ inputRange: [0, 0.12, 1], outputRange: [0.4, 1, 0.9] }) },
    ],
  }]} />;
}

const s = StyleSheet.create({
  stage: { alignItems: 'center', justifyContent: 'center', position: 'relative' },
  halo: { alignItems: 'center', borderRadius: 999, justifyContent: 'center' },
  seal: { alignItems: 'center', borderRadius: 999, elevation: 5, justifyContent: 'center', shadowColor: '#168B63', shadowOffset: { width: 0, height: 5 }, shadowOpacity: 0.25, shadowRadius: 8 },
  confetti: { position: 'absolute', zIndex: 2 },
  confettiSquare: { borderRadius: 2, height: 9, width: 9 },
  confettiStrip: { borderRadius: 2, height: 13, width: 6 },
});
