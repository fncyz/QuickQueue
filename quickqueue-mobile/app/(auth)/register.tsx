import { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Text, TextInput } from '@/components/Typography';
import { Ionicons } from "@expo/vector-icons";
import DateTimePicker from "@react-native-community/datetimepicker";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import type { StyleProp, ViewStyle } from "react-native";
import BarangayDropdown from "@/components/BarangayDropdown";
import AddressDropdown from "@/components/AddressDropdown";

import { registerResident } from "@/services/api";
import AsyncStorage from "@react-native-async-storage/async-storage";

const registrationErrorMessage = (error: any) => {
  if (!error?.response) {
    return "Cannot reach the QuickQueue server. Confirm that your phone and computer are on the same Wi-Fi, then restart the Django server.";
  }

  const errors = error.response.data?.errors;
  if (errors && typeof errors === "object") {
    return Object.entries(errors)
      .map(([field, messages]) => `${field.replace(/_/g, " ")}: ${(Array.isArray(messages) ? messages : [messages]).join(", ")}`)
      .join("\n");
  }
  return error.response.data?.message || "We could not create your account. Please try again.";
};

const formatDate = (date: Date | null) => {
  if (!date) return "mm/dd/yyyy";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const calculateAge = (date: Date | null) => {
  if (!date) return "";
  const today = new Date();
  let age = today.getFullYear() - date.getFullYear();
  const hasNotHadBirthday =
    today.getMonth() < date.getMonth() ||
    (today.getMonth() === date.getMonth() && today.getDate() < date.getDate());
  return String(hasNotHadBirthday ? age - 1 : age);
};

const provinces = [
    { id: 1, name: "Cebu" },
  ];

  const municipalities = [
    { id: 1, name: "Toledo City" },
  ];

function Field({ label, optional, required, children, style }: {
  label: string;
  optional?: boolean;
  required?: boolean;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View style={[styles.field, style]}>
      <Text style={styles.fieldLabel}>
        {label} {optional && <Text style={styles.optional}>(Optional)</Text>}
        {required && <Text style={styles.required}> *</Text>}
      </Text>
      {children}
    </View>
  );
}

function SectionTitle({ icon, children }: { icon: keyof typeof Ionicons.glyphMap; children: string }) {
  return (
    <View style={styles.sectionTitle}>
      <Ionicons name={icon} size={21} color="#1671FF" />
      <Text style={styles.sectionTitleText}>{children}</Text>
    </View>
  );
}

function IconInput({ icon, ...props }: React.ComponentProps<typeof TextInput> & { icon: keyof typeof Ionicons.glyphMap }) {
  return (
    <View style={styles.inputShell}>
      <Ionicons name={icon} size={16} color="#72809C" />
      <TextInput style={styles.inputText} placeholderTextColor="#98A2B7" {...props} />
    </View>
  );
}

export default function RegisterScreen() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [suffix, setSuffix] = useState("");
  const [birthdate, setBirthdate] = useState<Date | null>(null);
  const [sex, setSex] = useState("");
  const [showSexPicker, setShowSexPicker] = useState(false);
  const [email, setEmail] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [barangay, setBarangay] = useState<number | null>(null);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [province, setProvince] = useState<number | null>(null);
  const [municipality, setMunicipality] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleContactNumberChange = (value: string) => {
    const digitsOnly = value.replace(/\D/g, "");
    if (value !== digitsOnly) {
      Alert.alert("Invalid Contact Number", "Contact number can contain digits only.");
    }
    setContactNumber(digitsOnly);
  };

const handleRegister = async () => {
  if (!birthdate) {
    Alert.alert("Birthdate Required", "Please select your birthdate.");
    return;
  }

  if (!barangay) {
    Alert.alert("Barangay Required", "Please select your barangay.");
    return;
  }

  if (!acceptedTerms) {
    Alert.alert(
      "Terms & Conditions",
      "Please accept the Terms & Conditions."
    );
    return;
  }

  if (!username || !firstName || !lastName || !sex || !contactNumber) {
    Alert.alert("Required Information", "Please complete all required fields.");
    return;
  }

  if (!/^\d+$/.test(contactNumber)) {
    Alert.alert("Invalid Contact Number", "Contact number can contain digits only.");
    return;
  }

  try {
    setIsSubmitting(true);
    const result = await registerResident({
      username,
      first_name: firstName,
      last_name: lastName,
      middle_name: middleName,
      suffix,
      birthdate: formatDate(birthdate),
      sex,
      email: email.trim() || null,
      contact_number: contactNumber,
      barangay,
      terms_accepted: acceptedTerms,
    });

    await AsyncStorage.multiSet([
      ["quickqueue.accessToken", result.access],
      ["quickqueue.refreshToken", result.refresh],
      ["quickqueue.securitySetupStage", "password"],
      ["quickqueue.pendingUsername", result.username],
    ]);
    router.replace("/set-password");
  } catch (error: any) {
    Alert.alert("Registration Failed", registrationErrorMessage(error));
  } finally {
    setIsSubmitting(false);
  }
};

  return (
    <SafeAreaView style={styles.page} edges={["top", "bottom"]}>
      <KeyboardAvoidingView style={styles.keyboardView} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <View style={styles.card}>
            <Text style={styles.title}>Create Account</Text>
            <Text style={styles.subtitle}>Join us to get started</Text>

            <SectionTitle icon="person-outline">PERSONAL INFORMATION</SectionTitle>
            <View style={styles.row}>
              <Field label="First Name" required><IconInput icon="person-outline" placeholder="Enter first name" value={firstName} onChangeText={setFirstName} /></Field>
              <Field label="Middle Name" optional><IconInput icon="person-outline" placeholder="Enter middle name" value={middleName} onChangeText={setMiddleName} /></Field>
            </View>
            <Field label="Last Name" required><IconInput icon="person-outline" placeholder="Enter last name" value={lastName} onChangeText={setLastName} /></Field>
            <View style={styles.row}>
              <Field label="Suffix" optional><IconInput icon="pricetag-outline" placeholder="Enter suffix" value={suffix} onChangeText={setSuffix} /></Field>
              <Field label="Birthdate" required>
                <Pressable style={styles.dateInput} onPress={() => setShowDatePicker(true)}>
                  <Ionicons name="calendar-outline" size={16} color="#72809C" />
                  <Text style={[styles.dateText, !birthdate && styles.placeholder]}>{formatDate(birthdate)}</Text>
                  <Ionicons name="chevron-down" size={14} color="#72809C" />
                </Pressable>
              </Field>
            </View>
            <View style={styles.row}>
              <Field label="Age" required><View style={styles.inputShell}><Ionicons name="calendar-outline" size={16} color="#72809C" /><Text style={calculateAge(birthdate) ? styles.dateText : styles.placeholder}>{calculateAge(birthdate) || "Enter age"}</Text></View></Field>
              <Field label="Sex" required>
                <Pressable style={styles.selectInput} onPress={() => setShowSexPicker(true)} accessibilityRole="button" accessibilityLabel="Select sex">
                  <Ionicons name="person-outline" size={16} color="#72809C" /><Text style={[styles.selectText, sex ? styles.dateText : styles.placeholder]}>{sex === "M" ? "Male" : sex === "F" ? "Female" : "Select"}</Text><Ionicons name="chevron-down" size={14} color="#72809C" />
                </Pressable>
              </Field>
            </View>

            <SectionTitle icon="mail-outline">ACCOUNT INFORMATION</SectionTitle>
            <View style={styles.row}>
              <Field label="Username" required><IconInput icon="person-outline" placeholder="Enter username" value={username} onChangeText={setUsername} autoCapitalize="none" /></Field>
              <Field label="Contact Number" required><IconInput icon="call-outline" placeholder="Enter contact number" value={contactNumber} onChangeText={handleContactNumberChange} keyboardType="phone-pad" maxLength={15} /></Field>
            </View>
            <Field label="Email Address" optional><IconInput icon="mail-outline" placeholder="Enter email address (optional)" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" /></Field>
            <SectionTitle icon="location-outline">ADDRESS INFORMATION</SectionTitle>
            <View style={styles.row}>
              <Field label="Province" required>
                <AddressDropdown
                  placeholder="Select Province"
                  value={province}
                  options={provinces}
                  onValueChange={setProvince}
                  icon="business-outline"
                />
              </Field>

              <Field label="Municipality" required>
                <AddressDropdown
                  placeholder="Select Municipality"
                  value={municipality}
                  options={municipalities}
                  onValueChange={setMunicipality}
                  icon="business-outline"
                />
              </Field>
            </View>
            <Field label="Barangay" required>
            <BarangayDropdown
                value={barangay}
                onValueChange={setBarangay}
            />
            </Field>
            <View style={styles.actionArea}>
              <Pressable style={styles.termsBox} onPress={() => setAcceptedTerms((value) => !value)} accessibilityRole="checkbox" accessibilityState={{ checked: acceptedTerms }}>
                <View style={[styles.checkbox, acceptedTerms && styles.checkboxChecked]}>{acceptedTerms && <Ionicons name="checkmark" size={14} color="#fff" />}</View>
                <Text style={styles.termsText}>I have read and agree to the <Text style={styles.termsLink}>Terms</Text> and <Text style={styles.termsLink}>Privacy Policy.</Text><Text style={styles.required}> *</Text></Text>
              </Pressable>

              <Pressable style={[styles.createButton, isSubmitting && styles.createButtonDisabled]} onPress={handleRegister} disabled={isSubmitting} accessibilityRole="button" accessibilityState={{ disabled: isSubmitting }}><Text style={styles.createButtonText}>{isSubmitting ? "Creating Account..." : "Create Account"}</Text></Pressable>
              <View style={styles.signInRow}><Text style={styles.signInText}>Already have an account? </Text><Pressable onPress={() => router.replace("/login")}><Text style={styles.signInLink}>Sign In</Text></Pressable></View>
            </View>

          </View>
        </ScrollView>
      </KeyboardAvoidingView>
      {showDatePicker && <DateTimePicker value={birthdate ?? new Date()} mode="date" display="default" maximumDate={new Date()} onChange={(_, date) => { setShowDatePicker(Platform.OS === "ios"); if (date) setBirthdate(date); }} />}
      <Modal transparent animationType="fade" visible={showSexPicker} onRequestClose={() => setShowSexPicker(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setShowSexPicker(false)}>
          <View style={styles.sexMenu}>
            <Text style={styles.sexMenuTitle}>Select sex</Text>
            {[
              { label: "Male", value: "M" },
              { label: "Female", value: "F" },
            ].map((option) => (
              <Pressable
                key={option.value}
                style={styles.sexOption}
                onPress={() => { setSex(option.value); setShowSexPicker(false); }}
              >
                <Text style={styles.sexOptionText}>{option.label}</Text>
                {sex === option.value && <Ionicons name="checkmark" size={19} color="#1671FF" />}
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFFFFF" }, keyboardView: { flex: 1 }, scrollContent: { flexGrow: 1 },
  card: { backgroundColor: "#FFFFFF", flex: 1, paddingHorizontal: 17, paddingTop: 16, paddingBottom: 18 },
  title: { color: "#0E3978", fontSize: 27, fontWeight: "800", letterSpacing: -0.5, textAlign: "center" }, subtitle: { color: "#69738A", fontSize: 15, marginTop: 3, textAlign: "center" },
  sectionTitle: { alignItems: "center", borderBottomColor: "#EEF3FA", borderBottomWidth: 1, flexDirection: "row", gap: 12, marginTop: 24, marginBottom: 13, paddingBottom: 7 }, sectionTitleText: { color: "#086DFF", fontSize: 11, fontWeight: "700" },
  row: { flexDirection: "row", gap: 14 }, field: { flex: 1, marginBottom: 14 }, fieldLabel: { color: "#17366D", fontSize: 10, fontWeight: "700", marginBottom: 6 }, optional: { color: "#8A94A8", fontWeight: "400" }, required: { color: "#F02D2D" },
  inputShell: { alignItems: "center", backgroundColor: "#FFFFFF", borderColor: "#E8EEF6", borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: 10, height: 46, paddingHorizontal: 14, shadowColor: "#1D4F91", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.025, shadowRadius: 5, elevation: 1 },
  inputText: { color: "#273246", flex: 1, fontSize: 11, height: "100%", paddingVertical: 0 },
  dateInput: { alignItems: "center", backgroundColor: "#FFFFFF", borderColor: "#E8EEF6", borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: 9, height: 46, paddingHorizontal: 14, shadowColor: "#1D4F91", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.025, shadowRadius: 5, elevation: 1 }, dateText: { color: "#273246", fontSize: 11 }, placeholder: { color: "#98A2B7", fontSize: 10 },
  selectInput: { alignItems: "center", backgroundColor: "#FFFFFF", borderColor: "#E8EEF6", borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: 9, height: 46, paddingHorizontal: 14, shadowColor: "#1D4F91", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.025, shadowRadius: 5, elevation: 1 }, selectText: { flex: 1 },
  actionArea: { marginTop: "auto" },
  termsBox: { alignItems: "center", backgroundColor: "#F0F7FF", borderRadius: 10, flexDirection: "row", marginTop: 1, minHeight: 44, paddingHorizontal: 18, paddingVertical: 8 }, checkbox: { alignItems: "center", borderColor: "#30445F", borderRadius: 4, borderWidth: 1.5, height: 17, justifyContent: "center", marginRight: 10, width: 17 }, checkboxChecked: { backgroundColor: "#1671FF", borderColor: "#1671FF" }, termsText: { color: "#647087", flex: 1, fontSize: 9 }, termsLink: { color: "#1671FF" },
  createButton: { alignItems: "center", backgroundColor: "#17468F", borderRadius: 10, height: 43, justifyContent: "center", marginTop: 12 }, createButtonDisabled: { opacity: 0.65 }, createButtonText: { color: "#FFFFFF", fontSize: 13, fontWeight: "700" },
  signInRow: { alignItems: "center", flexDirection: "row", justifyContent: "center", marginVertical: 13 }, signInText: { color: "#69738A", fontSize: 10 }, signInLink: { color: "#1671FF", fontSize: 10, fontWeight: "600" },
  modalBackdrop: { alignItems: "center", backgroundColor: "rgba(0, 0, 0, 0.35)", flex: 1, justifyContent: "center", padding: 28 }, sexMenu: { backgroundColor: "#FFFFFF", borderRadius: 14, overflow: "hidden", width: "100%" }, sexMenuTitle: { color: "#163C7D", fontSize: 16, fontWeight: "700", paddingHorizontal: 18, paddingTop: 18, paddingBottom: 9 }, sexOption: { alignItems: "center", borderTopColor: "#E5E7EB", borderTopWidth: 1, flexDirection: "row", height: 50, justifyContent: "space-between", paddingHorizontal: 18 }, sexOptionText: { color: "#1D2738", fontSize: 15 },
});
