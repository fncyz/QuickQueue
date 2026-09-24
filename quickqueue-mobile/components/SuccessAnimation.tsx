import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

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

  return <Animated.View style={[s.halo, { height: size, opacity, transform: [{ scale: halo }], width: size }]}>
    <Animated.View style={[s.seal, { backgroundColor: color, height: size * 0.68, transform: [{ scale }], width: size * 0.68 }]}>
      <Ionicons name="checkmark" size={size * 0.45} color="#FFFFFF" />
    </Animated.View>
    <View style={[s.spark, s.sparkLeft, { backgroundColor: color }]} />
    <View style={[s.spark, s.sparkRight, { backgroundColor: color }]} />
  </Animated.View>;
}

const s = StyleSheet.create({
  halo: { alignItems: 'center', backgroundColor: 'rgba(57,204,145,0.14)', borderRadius: 999, justifyContent: 'center', position: 'relative' },
  seal: { alignItems: 'center', borderRadius: 999, elevation: 5, justifyContent: 'center', shadowColor: '#168B63', shadowOffset: { width: 0, height: 5 }, shadowOpacity: 0.25, shadowRadius: 8 },
  spark: { borderRadius: 4, height: 7, position: 'absolute', width: 7 },
  sparkLeft: { left: -9, top: 20 },
  sparkRight: { bottom: 18, right: -10 },
});
