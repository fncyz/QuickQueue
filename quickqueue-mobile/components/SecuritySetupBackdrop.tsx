import { StyleSheet, View } from "react-native";

export default function SecuritySetupBackdrop() {
  return <View pointerEvents="none" style={StyleSheet.absoluteFill}>
    <View style={s.blueGlow} />
    <View style={s.yellowGlow} />
    <View style={s.whiteWash} />
  </View>;
}

const s = StyleSheet.create({
  blueGlow: { backgroundColor: "#2F83EA", borderRadius: 180, height: 260, left: -115, opacity: 0.34, position: "absolute", top: -115, width: 300 },
  yellowGlow: { backgroundColor: "#FFE590", borderRadius: 150, height: 230, opacity: 0.55, position: "absolute", right: -110, top: -85, width: 250 },
  whiteWash: { backgroundColor: "rgba(255,255,255,0.42)", height: 150, left: 0, position: "absolute", right: 0, top: 80 },
});
