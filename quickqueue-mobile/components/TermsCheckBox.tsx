import { View, Text, Switch, StyleSheet } from "react-native";

interface Props {
  value: boolean;
  onValueChange: (value: boolean) => void;
}

export default function TermsCheckbox({
  value,
  onValueChange,
}: Props) {
  return (
    <View style={styles.container}>
      <Switch
        value={value}
        onValueChange={onValueChange}
      />

      <Text style={styles.text}>
        I agree to the Terms & Conditions
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
  },
  text: {
    marginLeft: 10,
    flex: 1,
    fontSize: 15,
  },
});

