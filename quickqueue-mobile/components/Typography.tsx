import { forwardRef } from 'react';
import {
  StyleSheet,
  Text as NativeText,
  TextInput as NativeTextInput,
  type TextInputProps,
  type TextProps,
  type TextStyle,
} from 'react-native';

const fontForWeight = (weight: TextStyle['fontWeight']) => {
  const normalized = String(weight ?? '400');
  if (normalized === 'bold' || Number.parseInt(normalized, 10) >= 700) return normalized === '800' || normalized === '900' ? 'Poppins_800ExtraBold' : 'Poppins_700Bold';
  if (Number.parseInt(normalized, 10) >= 600) return 'Poppins_600SemiBold';
  if (Number.parseInt(normalized, 10) >= 500) return 'Poppins_500Medium';
  return 'Poppins_400Regular';
};

export const Text = forwardRef<React.ElementRef<typeof NativeText>, TextProps>(({ style, ...props }, ref) => {
  const flattened = StyleSheet.flatten(style);
  return <NativeText ref={ref} allowFontScaling={false} maxFontSizeMultiplier={1} {...props} style={[style, { fontFamily: fontForWeight(flattened?.fontWeight) }]} />;
});
Text.displayName = 'Text';

export const TextInput = forwardRef<React.ElementRef<typeof NativeTextInput>, TextInputProps>(({ style, ...props }, ref) => {
  const flattened = StyleSheet.flatten(style);
  return <NativeTextInput ref={ref} allowFontScaling={false} maxFontSizeMultiplier={1} {...props} style={[style, { fontFamily: fontForWeight(flattened?.fontWeight) }]} />;
});
TextInput.displayName = 'TextInput';
