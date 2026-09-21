import { useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const barangays = [
  { id: 3, name: "Bato" },
  { id: 6, name: "Poblacion" },
];

interface Props {
  value: number | null;
  onValueChange: (value: number | null) => void;
}

export default function BarangayDropdown({
  value,
  onValueChange,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedBarangay = barangays.find((b) => b.id === value);

  return (
    <>
      <Pressable
        style={styles.trigger}
        onPress={() => setIsOpen(true)}
      >
        <Ionicons name="home-outline" size={16} color="#72809C" />
        <Text
          style={selectedBarangay ? styles.value : styles.placeholder}
        >
          {selectedBarangay?.name ?? "Select Barangay"}
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
            <Text style={styles.menuTitle}>Select Barangay</Text>

            <ScrollView>
              {barangays.map((barangay) => (
                <Pressable
                  key={barangay.id}
                  style={styles.option}
                  onPress={() => {
                    onValueChange(barangay.id);
                    setIsOpen(false);
                  }}
                >
                  <Text style={styles.optionText}>
                    {barangay.name}
                  </Text>

                  {value === barangay.id && (
                    <Ionicons
                      name="checkmark"
                      size={19}
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
    height: 46,
    justifyContent: "space-between",
    paddingHorizontal: 14,
  },
  value: { color: "#273246", flex: 1, fontSize: 11, marginRight: 8 },
  placeholder: { color: "#777E8D", flex: 1, fontSize: 10, marginRight: 8 },
  backdrop: {
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.35)",
    flex: 1,
    justifyContent: "center",
    padding: 28,
  },
  menu: { backgroundColor: "#FFFFFF", borderRadius: 14, maxHeight: "65%", overflow: "hidden", width: "100%" },
  menuTitle: { color: "#163C7D", fontSize: 16, fontWeight: "700", paddingHorizontal: 18, paddingTop: 18, paddingBottom: 9 },
  option: {
    alignItems: "center",
    borderTopColor: "#E5E7EB",
    borderTopWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 50,
    paddingHorizontal: 18,
  },
  optionText: { color: "#1D2738", fontSize: 15 },
});
