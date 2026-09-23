import { useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Text } from '@/components/Typography';
import { Ionicons } from "@expo/vector-icons";

interface Option {
  id: number;
  name: string;
}

interface Props {
  placeholder: string;
  value: number | null;
  options: Option[];
  onValueChange: (value: number) => void;
  icon?: keyof typeof Ionicons.glyphMap;
}

export default function AddressDropdown({
  placeholder,
  value,
  options,
  onValueChange,
  icon = "business-outline",
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const selected = options.find((o) => o.id === value);

  return (
    <>
      <Pressable
        style={styles.trigger}
        onPress={() => setIsOpen(true)}
      >
        <Ionicons name={icon} size={16} color="#72809C" />
        <Text style={selected ? styles.value : styles.placeholder}>
          {selected?.name ?? placeholder}
        </Text>

        <Ionicons
          name="chevron-down"
          size={14}
          color="#18233C"
        />
      </Pressable>

      <Modal
        transparent
        animationType="fade"
        visible={isOpen}
        onRequestClose={() => setIsOpen(false)}
      >
        <Pressable
          style={styles.backdrop}
          onPress={() => setIsOpen(false)}
        >
          <View style={styles.menu}>
            <Text style={styles.menuTitle}>{placeholder}</Text>

            <ScrollView>
              {options.map((option) => (
                <Pressable
                  key={option.id}
                  style={styles.option}
                  onPress={() => {
                    onValueChange(option.id);
                    setIsOpen(false);
                  }}
                >
                  <Text style={styles.optionText}>
                    {option.name}
                  </Text>

                  {value === option.id && (
                    <Ionicons
                      name="checkmark"
                      size={18}
                      color="#1671FF"
                    />
                  )}
                </Pressable>
              ))}
            </ScrollView>
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#EEF2F7",
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
    height: 46,
    paddingHorizontal: 14,
  },

  value: {
    flex: 1,
    color: "#273246",
    fontSize: 11,
  },

  placeholder: {
    flex: 1,
    color: "#777E8D",
    fontSize: 10,
  },

  backdrop: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,.35)",
    padding: 28,
  },

  menu: {
    width: "100%",
    maxHeight: "65%",
    backgroundColor: "#fff",
    borderRadius: 14,
    overflow: "hidden",
  },

  menuTitle: {
    padding: 18,
    fontSize: 16,
    fontWeight: "700",
    color: "#163C7D",
  },

  option: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: 50,
    paddingHorizontal: 18,
    borderTopWidth: 1,
    borderTopColor: "#E5E7EB",
  },

  optionText: {
    fontSize: 15,
    color: "#1D2738",
  },
});
