import { Image, StyleSheet, View } from "react-native";

const securityBackground = require("../assets/images/secbg.jpg");

export default function SecuritySetupBackdrop() {
  return <View pointerEvents="none" style={[StyleSheet.absoluteFill, s.backdrop]}>
    <Image source={securityBackground} resizeMode="cover" style={s.image} />
  </View>;
}

const s = StyleSheet.create({
  backdrop: { backgroundColor: "#FFFFFF" },
  image: { bottom: 0, height: "100%", position: "absolute", right: 0, width: "115%" },
});
