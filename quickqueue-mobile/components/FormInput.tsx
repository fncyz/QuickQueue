import { StyleSheet, TextInputProps } from "react-native";
import { TextInput } from '@/components/Typography';

type FormInputProps = TextInputProps;

export default function FormInput(props: FormInputProps) {
  return (
    <TextInput
      {...props}
      style={[styles.input, props.style]}
      placeholderTextColor="#999"
    />
  );
}

const styles = StyleSheet.create({
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    fontSize: 16,
    backgroundColor: "#fff",
  },
});
