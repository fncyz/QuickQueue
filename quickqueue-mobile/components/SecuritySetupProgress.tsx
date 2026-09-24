import { Ionicons } from "@expo/vector-icons";
import { StyleSheet, View } from "react-native";
import { Text } from "@/components/Typography";

const steps = ["Create\nPassword", "Enter\nPasskey", "Enable\nFingerprint", "Face\nRecognition"];

export default function SecuritySetupProgress({ current }: { current: number }) {
  return <View style={s.wrap}>{steps.map((label, index) => {
    const number = index + 1;
    const complete = number < current;
    const active = number === current;
    return <View key={label} style={s.step}>
      <View style={[s.circle, (active || complete) && s.circleActive]}>{complete ? <Ionicons name="checkmark" size={13} color="#FFF" /> : <Text style={[s.number, active && s.numberActive]}>{number}</Text>}</View>
      <Text style={[s.label, active && s.labelActive, complete && s.labelComplete]}>{label}</Text>
      {index < steps.length - 1 && <View style={[s.line, complete && s.lineComplete]} />}
    </View>;
  })}</View>;
}

const s = StyleSheet.create({
  wrap: { flexDirection: "row", marginBottom: 27, paddingHorizontal: 0 },
  step: { alignItems: "center", flex: 1, position: "relative" },
  circle: { alignItems: "center", backgroundColor: "#FFFFFF", borderColor: "#C9D8ED", borderRadius: 12, borderWidth: 1, height: 24, justifyContent: "center", width: 24, zIndex: 2 },
  circleActive: { backgroundColor: "#0966E8", borderColor: "#0966E8" },
  number: { color: "#6E82A0", fontSize: 10, fontWeight: "700" },
  numberActive: { color: "#FFF" },
  label: { color: "#7185A3", fontSize: 9, lineHeight: 12, marginTop: 5, textAlign: "center" },
  labelActive: { color: "#073A91", fontWeight: "700" },
  labelComplete: { color: "#073A91", fontWeight: "600" },
  line: { backgroundColor: "#CAD7E9", height: 1.5, left: "65%", position: "absolute", top: 11, width: "70%" },
  lineComplete: { backgroundColor: "#0966E8" },
});
