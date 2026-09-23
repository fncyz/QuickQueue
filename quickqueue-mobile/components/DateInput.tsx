import { useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
} from "react-native";
import { Text } from '@/components/Typography';

import DateTimePicker from "@react-native-community/datetimepicker";

interface Props {
  value: Date;
  onChange: (date: Date) => void;
}

export default function DateInput({
  value,
  onChange,
}: Props) {
  const [show, setShow] = useState(false);

  return (
    <>
      <Pressable
        style={styles.input}
        onPress={() => setShow(true)}
      >
        <Text>
          {value.toISOString().split("T")[0]}
        </Text>
      </Pressable>

      {show && (
        <DateTimePicker
          value={value}
          mode="date"
          display="default"
          maximumDate={new Date()}
          onChange={(event, selectedDate) => {
            setShow(Platform.OS === "ios");

            if (selectedDate) {
              onChange(selectedDate);
            }
          }}
        />
      )}
    </>
  );
}

const styles = StyleSheet.create({
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    backgroundColor: "#fff",
  },
});
