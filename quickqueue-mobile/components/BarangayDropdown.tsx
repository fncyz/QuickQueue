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
import { useAppTheme } from '@/contexts/app-theme';
import { appTypography } from '@/constants/typography';

const barangays = [
  { id: 5, name: "Daanlungsod" },
  { id: 2, name: "Luray 2" },
  { id: 1, name: "Poblacion" },
  { id: 4, name: "Sangi" },
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
  const { colors } = useAppTheme();

  const selectedBarangay = barangays.find((b) => b.id === value);

  return (
    <>
      <Pressable
        style={[styles.trigger, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}
        onPress={() => setIsOpen(true)}
      >
        <Ionicons name="home-outline" size={16} color={colors.muted} />
        <Text
          fixedFontSize={9}
          style={[selectedBarangay ? styles.value : styles.placeholder, { color: selectedBarangay ? colors.text : colors.muted }]}
        >
          {selectedBarangay?.name ?? "Select Barangay"}
        </Text>

        <Ionicons
          name="chevron-down"
          size={14}
          color={colors.muted}
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
          <View style={[styles.menu, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text fixedFontSize={9} style={[styles.menuTitle, { color: colors.text }]}>Select Barangay</Text>

            <ScrollView>
              {barangays.map((barangay) => (
                <Pressable
                  key={barangay.id}
                  style={[styles.option, { borderTopColor: colors.border }]}
                  onPress={() => {
                    onValueChange(barangay.id);
                    setIsOpen(false);
                  }}
                >
                  <Text fixedFontSize={9} style={[styles.optionText, { color: colors.text }]}>                                    
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
  value: { ...appTypography.input, color: "#273246", flex: 1, fontSize: 9, lineHeight: 13, marginRight: 8 },
  placeholder: { ...appTypography.input, color: "#777E8D", flex: 1, fontSize: 9, lineHeight: 13, marginRight: 8 },
  backdrop: {
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.35)",
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 18,
    paddingVertical: 28,
  },
  menu: { backgroundColor: "#FFFFFF", borderRadius: 14, borderWidth: 1, maxHeight: "65%", maxWidth: 520, overflow: "hidden", width: "100%" },
  menuTitle: { ...appTypography.sectionTitle, color: "#163C7D", fontSize: 9, lineHeight: 13, paddingHorizontal: 18, paddingTop: 18, paddingBottom: 9 },
  option: {
    alignItems: "center",
    borderTopColor: "#E5E7EB",
    borderTopWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 50,
    paddingHorizontal: 18,
  },
  optionText: { ...appTypography.body, color: "#1D2738", fontSize: 9, lineHeight: 13 },
});
