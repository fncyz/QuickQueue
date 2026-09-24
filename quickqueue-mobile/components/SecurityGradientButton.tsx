import { LinearGradient } from "expo-linear-gradient";
import { Pressable, StyleProp, StyleSheet, ViewStyle } from "react-native";

import { Text } from "@/components/Typography";

type Props = {
  disabled?: boolean;
  label: string;
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
};

export default function SecurityGradientButton({ disabled = false, label, onPress, style }: Props) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={[s.button, style, disabled && s.disabled]}>
    <LinearGradient colors={["#003B91", "#075BCF", "#0784FF"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={s.gradient}>
      <Text style={s.label}>{label}</Text>
    </LinearGradient>
  </Pressable>;
}

const s = StyleSheet.create({
  button: { borderRadius: 25, elevation: 8, shadowColor: "#0874F9", shadowOffset: { width: 0, height: 7 }, shadowOpacity: 0.27, shadowRadius: 10 },
  disabled: { opacity: 0.48 },
  gradient: { alignItems: "center", borderRadius: 25, justifyContent: "center", minHeight: 48, paddingHorizontal: 18 },
  label: { color: "#FFF", fontSize: 13, fontWeight: "700" },
});
