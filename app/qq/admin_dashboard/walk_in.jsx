import { useState } from 'react'
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  useWindowDimensions,
  TextInput,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const PRIORITY_OPTIONS = ['Senior Citizen', 'Person with Disability (PWD)', 'Pregnant']

const WalkInRegistrationScreen = () => {
  const router = useRouter()
  const { width } = useWindowDimensions()
  const isCompact = width < 1100
  const isMobile = width < 760

  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    middleInitial: '',
    suffix: '',
    contactNumber: '',
    maritalStatus: '',
    streetName: '',
    serviceRequested: '',
  })
  const [selectedPriority, setSelectedPriority] = useState(null)

  const togglePriority = (label) => {
    setSelectedPriority((current) => (current === label ? null : label))
  }

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.screenContent}>
      <View style={styles.topBar}>
        <Text style={styles.topBarTitle}>Admin Panel</Text>
        <TouchableOpacity style={styles.logoutButton} onPress={() => router.replace('/qq/res_login')}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.mainLayout, isCompact && styles.mainLayoutStack]}>
        <SideNavbar activeItem="Walk-In Registration" />

        <View style={styles.contentPane}>
          <View style={styles.headerBlock}>
            <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>Walk-In Registration</Text>
            <Text style={styles.headerSubtitle}>Register walk-in residents</Text>
          </View>

          <View style={[styles.formCard, isMobile && styles.formCardMobile]}>
            <View style={[styles.formRow, isMobile && styles.formRowMobile]}>
              <View style={[styles.fieldGroup, styles.fieldLarge]}>
                <Text style={styles.fieldLabel}>First Name</Text>
                <TextInput
                  value={form.firstName}
                  onChangeText={(value) => updateField('firstName', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>

              <View style={[styles.fieldGroup, styles.fieldMedium]}>
                <Text style={styles.fieldLabel}>Last Name</Text>
                <TextInput
                  value={form.lastName}
                  onChangeText={(value) => updateField('lastName', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>

              <View style={[styles.fieldGroup, styles.fieldSmall]}>
                <Text style={styles.fieldLabel}>Middle Initial</Text>
                <TextInput
                  value={form.middleInitial}
                  onChangeText={(value) => updateField('middleInitial', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>

              <View style={[styles.fieldGroup, styles.fieldTiny]}>
                <Text style={styles.fieldLabel}>Suffix</Text>
                <TextInput
                  value={form.suffix}
                  onChangeText={(value) => updateField('suffix', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>
            </View>

            <View style={[styles.formRow, isMobile && styles.formRowMobile]}>
              <View style={[styles.fieldGroup, styles.fieldLarge]}>
                <Text style={styles.fieldLabel}>Contact Number</Text>
                <TextInput
                  value={form.contactNumber}
                  onChangeText={(value) => updateField('contactNumber', value)}
                  style={styles.input}
                  keyboardType="phone-pad"
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>

              <View style={[styles.fieldGroup, styles.fieldMedium]}>
                <Text style={styles.fieldLabel}>Marital Status</Text>
                <TextInput
                  value={form.maritalStatus}
                  onChangeText={(value) => updateField('maritalStatus', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>

              <View style={[styles.fieldGroup, styles.fieldLarge]}>
                <Text style={styles.fieldLabel}>Street Name</Text>
                <TextInput
                  value={form.streetName}
                  onChangeText={(value) => updateField('streetName', value)}
                  style={styles.input}
                  placeholder=""
                  placeholderTextColor="#94A3B8"
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Service Requested</Text>
              <TouchableOpacity activeOpacity={0.85} style={styles.selectField}>
                <Text style={styles.selectPlaceholder}>
                  {form.serviceRequested || 'Select Service...'}
                </Text>
                <Ionicons name="chevron-down-outline" size={28} color="#60A5FA" />
              </TouchableOpacity>
            </View>

            <View style={styles.prioritySection}>
              <Text style={styles.fieldLabel}>Priority Status</Text>

              {PRIORITY_OPTIONS.map((option) => {
                const isSelected = selectedPriority === option

                return (
                  <TouchableOpacity
                    key={option}
                    activeOpacity={0.85}
                    style={styles.checkboxRow}
                    onPress={() => togglePriority(option)}
                  >
                    <View style={[styles.checkbox, isSelected && styles.checkboxSelected]}>
                      {isSelected ? <Ionicons name="checkmark" size={14} color="#FFFFFF" /> : null}
                    </View>
                    <Text style={styles.checkboxLabel}>{option}</Text>
                  </TouchableOpacity>
                )
              })}
            </View>

            <TouchableOpacity activeOpacity={0.85} style={styles.submitButton}>
              <Text style={styles.submitButtonText}>Register Walk-In</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#284B97',
  },
  screenContent: {
    minHeight: '100%',
  },
  topBar: {
    backgroundColor: '#C9DFF4',
    paddingHorizontal: 28,
    paddingVertical: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  topBarTitle: {
    fontSize: 32,
    fontWeight: '800',
    color: '#000000',
  },
  logoutButton: {
    backgroundColor: '#26488F',
    borderRadius: 999,
    minWidth: 190,
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 24,
  },
  logoutText: {
    color: '#FF4B2B',
    fontSize: 22,
    fontWeight: '700',
  },
  mainLayout: {
    flexDirection: 'row',
    flex: 1,
  },
  mainLayoutStack: {
    flexDirection: 'column',
  },
  contentPane: {
    flex: 1,
    backgroundColor: '#284B97',
    paddingHorizontal: 28,
    paddingTop: 28,
    paddingBottom: 40,
  },
  headerBlock: {
    marginHorizontal: 72,
    marginBottom: 22,
  },
  headerTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
  },
  headerTitleMobile: {
    fontSize: 36,
  },
  headerSubtitle: {
    fontSize: 20,
    color: '#F3F4F6',
    marginTop: 6,
    fontWeight: '500',
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 68,
    paddingHorizontal: 36,
    paddingVertical: 30,
  },
  formCardMobile: {
    marginHorizontal: 0,
    paddingHorizontal: 20,
  },
  formRow: {
    flexDirection: 'row',
    gap: 24,
    marginBottom: 14,
  },
  formRowMobile: {
    flexDirection: 'column',
    gap: 14,
  },
  fieldGroup: {
    marginBottom: 12,
  },
  fieldLarge: {
    flex: 1.3,
  },
  fieldMedium: {
    flex: 1,
  },
  fieldSmall: {
    flex: 0.7,
  },
  fieldTiny: {
    flex: 0.45,
  },
  fieldLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#000000',
    marginBottom: 8,
  },
  input: {
    height: 72,
    borderRadius: 10,
    backgroundColor: '#DBEAFE',
    paddingHorizontal: 18,
    fontSize: 18,
    color: '#111827',
  },
  selectField: {
    height: 72,
    borderRadius: 10,
    backgroundColor: '#DBEAFE',
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectPlaceholder: {
    fontSize: 18,
    color: '#60A5FA',
    fontWeight: '400',
  },
  prioritySection: {
    marginTop: 8,
    marginBottom: 28,
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 1.5,
    borderColor: '#A1A1AA',
    borderRadius: 4,
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  checkboxSelected: {
    backgroundColor: '#274C97',
    borderColor: '#274C97',
  },
  checkboxLabel: {
    fontSize: 18,
    color: '#111111',
    fontWeight: '400',
  },
  submitButton: {
    backgroundColor: '#274C97',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 62,
  },
  submitButtonText: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default WalkInRegistrationScreen
