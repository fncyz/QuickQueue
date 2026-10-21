import { useEffect, useRef } from 'react';
import { Animated, Easing, Image, StyleSheet, View } from 'react-native';
import { getStartupElapsedMs } from '@/services/startup-loading';

const centerLogo = require('../assets/images/splash_1.png');
const outerRing = require('../assets/images/splash_2.png');
const ROTATION_DURATION_MS = 1800;

// The visible ring is 8.5 px left of center inside its 500 px transparent canvas.
// Offset the layer itself and rotate around the ring's actual center. Translating the
// image inside a center-rotated layer makes that offset orbit and produces a wobble.
const RING_CENTER_OFFSET_RATIO = 8.5 / 500;

export function QuickQueueLoadingScreen() {
  return <View style={s.screen}><QuickQueueLoadingIndicator size={132} /></View>;
}

export function QuickQueueLoadingIndicator({ size = 72 }: { size?: number }) {
  const initialProgress = useRef((getStartupElapsedMs() % ROTATION_DURATION_MS) / ROTATION_DURATION_MS).current;
  const rotation = useRef(new Animated.Value(initialProgress)).current;

  useEffect(() => {
    const animation = Animated.sequence([
      Animated.timing(rotation, {
        duration: ROTATION_DURATION_MS * (1 - initialProgress),
        easing: Easing.linear,
        isInteraction: false,
        toValue: 1,
        useNativeDriver: true,
      }),
      Animated.timing(rotation, { duration: 0, toValue: 0, useNativeDriver: true }),
      Animated.loop(
        Animated.timing(rotation, {
          duration: ROTATION_DURATION_MS,
          easing: Easing.linear,
          isInteraction: false,
          toValue: 1,
          useNativeDriver: true,
        }),
        { resetBeforeIteration: true },
      ),
    ]);
    animation.start();
    return () => animation.stop();
  }, [initialProgress, rotation]);

  const rotate = rotation.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const ringOffset = size * RING_CENTER_OFFSET_RATIO;

  return <View accessibilityLabel="QuickQueue is loading" accessibilityRole="progressbar" style={[s.logoFrame, { height: size, width: size }]}> 
      <Animated.View
        style={[
          s.rotatingLayer,
          {
            left: ringOffset,
            transform: [{ rotate }],
            transformOrigin: [size / 2 - ringOffset, size / 2, 0],
          },
        ]}
      >
        <Image source={outerRing} resizeMode="contain" style={s.layer} />
      </Animated.View>
      <Image source={centerLogo} resizeMode="contain" style={s.layer} />
  </View>;
}

const s = StyleSheet.create({
  screen: { alignItems: 'center', backgroundColor: '#FFFFFF', flex: 1, justifyContent: 'center' },
  logoFrame: { alignItems: 'center', aspectRatio: 1, justifyContent: 'center', position: 'relative' },
  rotatingLayer: {
    aspectRatio: 1,
    height: '100%',
    position: 'absolute',
    top: 0,
    width: '100%',
  },
  layer: { height: '100%', left: 0, position: 'absolute', top: 0, width: '100%' },
});
