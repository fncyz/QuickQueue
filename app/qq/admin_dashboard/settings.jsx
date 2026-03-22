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
import SideNavbar from './side_navbar'

const SettingsScreen = () => {
  const router = useRouter()
  const { width } = useWindowDimensions()
  const isCompact = width < 1100
  const isMobile = width < 760

  const [config, setConfig] = useState({
    barangayName: '',
    cityMunicipality: '',
    contactNumber: '',
  })

  const updateField = (field, value) => {
    setConfig((current) => ({ ...current, [field]: value }))
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
        <SideNavbar activeItem="Settings" />

        <View style={styles.contentPane}>
          <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>System Configuration</Text>

          <View style={[styles.formCard, isMobile && styles.formCardMobile]}>
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Barangay Name</Text>
              <TextInput
                value={config.barangayName}
                onChangeText={(value) => updateField('barangayName', value)}
                style={styles.input}
                placeholder=""
                placeholderTextColor="#94A3B8"
              />
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>City/Municipality</Text>
              <TextInput
                value={config.cityMunicipality}
                onChangeText={(value) => updateField('cityMunicipality', value)}
                style={styles.input}
                placeholder=""
                placeholderTextColor="#94A3B8"
              />
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Contact Number</Text>
              <TextInput
                value={config.contactNumber}
                onChangeText={(value) => updateField('contactNumber', value)}
                style={styles.input}
                keyboardType="phone-pad"
                placeholder=""
                placeholderTextColor="#94A3B8"
              />
            </View>

            <TouchableOpacity activeOpacity={0.85} style={styles.saveButton}>
              <Text style={styles.saveButtonText}>Save Changes</Text>
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
  headerTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
    marginHorizontal: 58,
    marginBottom: 34,
  },
  headerTitleMobile: {
    fontSize: 36,
    marginHorizontal: 0,
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 34,
    marginHorizontal: 146,
    paddingHorizontal: 42,
    paddingVertical: 36,
  },
  formCardMobile: {
    marginHorizontal: 0,
    paddingHorizontal: 20,
  },
  fieldGroup: {
    marginBottom: 24,
  },
  fieldLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#000000',
    marginBottom: 10,
  },
  input: {
    height: 62,
    borderRadius: 16,
    backgroundColor: '#DBEAFE',
    paddingHorizontal: 18,
    fontSize: 18,
    color: '#111827',
  },
  saveButton: {
    alignSelf: 'center',
    marginTop: 10,
    minWidth: 492,
    minHeight: 66,
    borderRadius: 16,
    backgroundColor: '#67A2E3',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default SettingsScreen
