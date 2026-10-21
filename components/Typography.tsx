import { forwardRef } from 'react';
import {
  StyleSheet,
  Text as NativeText,
  TextInput as NativeTextInput,
  type TextInputProps,
  type TextProps,
  type TextStyle,
} from 'react-native';

type AppTextProps = TextProps & { fixedFontSize?: number };
type AppTextInputProps = TextInputProps & { fixedFontSize?: number };

const fontForWeight = (weight: TextStyle['fontWeight']) => {
  const normalized = String(weight ?? '400');
  if (normalized === 'bold' || Number.parseInt(normalized, 10) >= 700) return normalized === '800' || normalized === '900' ? 'Poppins_800ExtraBold' : 'Poppins_700Bold';
  if (Number.parseInt(normalized, 10) >= 600) return 'Poppins_600SemiBold';
  if (Number.parseInt(normalized, 10) >= 500) return 'Poppins_500Medium';
  return 'Poppins_400Regular';
};

/**
 * App-owned type scale. Legacy screens used many one-off sizes (some as small as
 * 5.5px); map their existing hierarchy onto a readable, device-independent
 * scale without deriving typography from screen dimensions.
 */
const fixedTextSize = (requested: number | undefined) => {
  const size = requested ?? 15;

  if (size >= 27) return 25;
  if (size >= 23) return 24;
  if (size >= 19) return 20;
  if (size >= 17) return 17;
  if (size >= 16) return 16;
  if (size >= 15) return 15;
  if (size >= 14) return 14;
  if (size >= 13) return 13;
  if (size >= 11) return 13;
  return 12;
};

const readableLineHeight = (fontSize: number) => Math.ceil(fontSize * 1.35);

export const Text = forwardRef<React.ElementRef<typeof NativeText>, AppTextProps>(({ fixedFontSize, style, ...props }, ref) => {
  const flattened = StyleSheet.flatten(style);
  const fontSize = fixedFontSize ?? fixedTextSize(flattened?.fontSize);
  const lineHeight = Math.max(flattened?.lineHeight ?? 0, readableLineHeight(fontSize));
  return <NativeText ref={ref} {...props} adjustsFontSizeToFit={false} allowFontScaling={false} minimumFontScale={1} style={[style, { fontFamily: fontForWeight(flattened?.fontWeight), fontSize, fontWeight: undefined, lineHeight }]} />;
});
Text.displayName = 'Text';

export const TextInput = forwardRef<React.ElementRef<typeof NativeTextInput>, AppTextInputProps>(({ fixedFontSize, style, ...props }, ref) => {
  const flattened = StyleSheet.flatten(style);
  return <NativeTextInput
    ref={ref}
    returnKeyType={props.returnKeyType ?? (props.multiline ? 'default' : 'done')}
    {...props}
    allowFontScaling={false}
    style={[style, { fontFamily: fontForWeight(flattened?.fontWeight), fontSize: fixedFontSize ?? 15, fontWeight: undefined, lineHeight: fixedFontSize ? readableLineHeight(fixedFontSize) : 21 }]}
  />;
});
TextInput.displayName = 'TextInput';
