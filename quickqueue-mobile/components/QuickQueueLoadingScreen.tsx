import { useEffect, useRef } from 'react';
import { Animated, Easing, Image, StyleSheet, View } from 'react-native';
import { getStartupElapsedMs } from '@/services/startup-loading';

const centerLogo = require('../assets/images/splash_1.png');
const outerRing = require('../assets/images/splash_2.png');

export function QuickQueueLoadingScreen() {
  return <View style={s.screen}><QuickQueueLoadingIndicator size={132} /></View>;
}

export function QuickQueueLoadingIndicator({ size = 72 }: { size?: number }) {
  const cycleDuration = 1800;
  const initialProgress = useRef((getStartupElapsedMs() % cycleDuration) / cycleDuration).current;
  const rotation = useRef(new Animated.Value(initialProgress)).current;

  useEffect(() => {
    const fullRotation = Animated.timing(rotation, {
        duration: 1800,
        easing: Easing.linear,
        toValue: 1,
        useNativeDriver: true,
      });
    const animation = Animated.sequence([
      Animated.timing(rotation, { duration: cycleDuration * (1 - initialProgress), easing: Easing.linear, toValue: 1, useNativeDriver: true }),
      Animated.timing(rotation, { duration: 0, toValue: 0, useNativeDriver: true }),
      Animated.loop(fullRotation),
    ]);
    animation.start();
    return () => animation.stop();
  }, [initialProgress, rotation]);

  const rotate = rotation.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });

  return <View accessibilityLabel="QuickQueue is loading" accessibilityRole="progressbar" style={[s.logoFrame, { height: size, width: size }]}> 
      <Animated.Image source={outerRing} resizeMode="contain" style={[s.layer, { transform: [{ rotate }] }]} />
      <Image source={centerLogo} resizeMode="contain" style={s.layer} />
  </View>;
}

const s = StyleSheet.create({
  screen: { alignItems: 'center', backgroundColor: '#FFFFFF', flex: 1, justifyContent: 'center' },
  logoFrame: { position: 'relative' },
  layer: { height: '100%', left: 0, position: 'absolute', top: 0, width: '100%' },
});
