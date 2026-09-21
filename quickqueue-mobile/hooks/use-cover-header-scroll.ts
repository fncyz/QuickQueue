import { useRef } from 'react';
import { Animated } from 'react-native';

/** Keeps a header visually fixed so the scrolling body covers it from below. */
export function useCoverHeaderScroll() {
  const scrollY = useRef(new Animated.Value(0)).current;
  const opacity = scrollY.interpolate({
    inputRange: [0, 90],
    outputRange: [1, 0],
    extrapolate: 'clamp',
  });

  return {
    headerStyle: { opacity, transform: [{ translateY: scrollY }] },
    onScroll: Animated.event(
      [{ nativeEvent: { contentOffset: { y: scrollY } } }],
      { useNativeDriver: true },
    ),
  };
}
