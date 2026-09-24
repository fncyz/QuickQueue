import { Image, StyleSheet, View } from "react-native";

const securityBackground = require("../assets/images/secbg.png");

export default function SecuritySetupBackdrop() {
  return <View pointerEvents="none" style={[StyleSheet.absoluteFill, s.backdrop]}>
    <Image source={securityBackground} resizeMode="contain" style={StyleSheet.absoluteFillObject} />
  </View>;
}

const s = StyleSheet.create({
  backdrop: { backgroundColor: "#FFFFFF" },
});
