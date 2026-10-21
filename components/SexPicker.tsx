import { Picker } from "@react-native-picker/picker";

interface Props {
  value: string;
  onValueChange: (value: string) => void;
}

export default function SexPicker({
  value,
  onValueChange,
}: Props) {
  return (
    <Picker
      selectedValue={value}
      onValueChange={onValueChange}
    >
      <Picker.Item label="Male" value="M" />
      <Picker.Item label="Female" value="F" />
    </Picker>
  );
}