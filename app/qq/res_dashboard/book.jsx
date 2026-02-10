import React, { useState } from 'react'
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  TextInput,
  Switch,
  Modal,
  Pressable,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import DateTimePicker from '@react-native-community/datetimepicker'

const Book = () => {
  const router = useRouter()

  const [showService, setShowService] = useState(false)
  const [showTime, setShowTime] = useState(false)
  const [showDate, setShowDate] = useState(false)

  const [service, setService] = useState('')
  const [timeSlot, setTimeSlot] = useState('')
  const [date, setDate] = useState(null)
  const [priority, setPriority] = useState(false)

  const services = [
    'Barangay Clearance',
    'Certificate of Residency',
    'Business Permit Application',
    'Barangay ID',
    'File Complaint',
  ]

  const timeSlots = [
    '8:00 AM - 9:00 AM',
    '9:00 AM - 10:00 AM',
    '10:00 AM - 11:00 AM',
    '1:00 PM - 2:00 PM',
    '2:00 PM - 3:00 PM',
    '3:00 PM - 4:00 PM',
  ]

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top navigation bar - same as res_index */}
      <View style={styles.navbar}>
        <View style={styles.navLeft}>
          <Image
            source={require('../../../assets/images/qq-logo.png')}
            style={styles.mainLogo}
            resizeMode="contain"
          />
          <Image
            source={require('../../../assets/images/toledo.png')}
            style={styles.partnerLogo}
            resizeMode="contain"
          />
          <Image
            source={require('../../../assets/images/cctc.png')}
            style={styles.partnerLogo}
            resizeMode="contain"
          />
        </View>

        <View style={styles.navLinks}>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => router.push('/qq/res_dashboard/res_index')}
          >
            <Text style={styles.navLink}>Home</Text>
          </TouchableOpacity>
          <TouchableOpacity activeOpacity={0.7} onPress={() => router.push('/qq/res_dashboard/book')}>
            <Text style={[styles.navLink, styles.navLinkActive]}>Book Now</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {}}
          >
            <Text style={styles.navLink}>Queue Status</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {}}
          >
            <Text style={styles.navLink}>About</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => router.replace('/qq/res_login')}
        >
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* Header - same hero section styling as res_index */}
      <View style={styles.heroSection}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>ONLINE BOOKING</Text>
        </View>
        <Text style={styles.heroTitle}>Schedule Your Appointment</Text>
        <Text style={styles.heroSubtitle}>
          Book your visit in advance and skip the waiting room. Get instant confirmation
          and queue number.
        </Text>
      </View>

      {/* Form card - same card style as res_index */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Personal Information</Text>
        <View style={styles.cardDivider} />

        {/* NAME */}
        <View style={styles.row}>
          <TextInput placeholder="First Name" style={styles.input} />
          <TextInput placeholder="Last Name" style={styles.input} />
          <TextInput placeholder="Middle Initial" style={styles.input} />
        </View>

        {/* ADDRESS */}
        <View style={styles.row}>
          <TextInput placeholder="Suffix (Extension)" style={styles.input} />
          <TextInput placeholder="Street Name" style={styles.input} />
          <TextInput placeholder="Contact Number" style={styles.input} />
        </View>

        {/* SERVICE */}
        <Text style={styles.label}>Service Type</Text>
        <Pressable style={styles.dropdown} onPress={() => setShowService(true)}>
          <Text style={styles.dropText}>{service || 'Select a service'}</Text>
          <Ionicons name="chevron-down" size={20} color="#6B7280" />
        </Pressable>

        {/* DATE */}
        <Text style={styles.label}>Date</Text>
        <Pressable style={styles.dropdown} onPress={() => setShowDate(true)}>
          <Text style={styles.dropText}>
            {date ? date.toLocaleDateString() : 'dd/mm/yyyy'}
          </Text>
          <Ionicons name="calendar-outline" size={20} color="#6B7280" />
        </Pressable>

        {/* TIME */}
        <Text style={styles.label}>Time Slot</Text>
        <Pressable style={styles.dropdown} onPress={() => setShowTime(true)}>
          <Text style={styles.dropText}>{timeSlot || 'Select time...'}</Text>
          <Ionicons name="chevron-down" size={20} color="#6B7280" />
        </Pressable>

        {/* NOTES */}
        <TextInput
          placeholder="Any special requests or information..."
          style={styles.textArea}
          multiline
        />

        {/* PRIORITY */}
        <View style={styles.priorityRow}>
          <Switch value={priority} onValueChange={setPriority} />
          <Text style={styles.priorityText}>
            I am a senior citizen (60+), PWD, or pregnant and would like priority assistance
          </Text>
        </View>

        <Text style={styles.note}>
          (Priority assistance is subject to verification by barangay staff upon arrival.)
        </Text>

        <TouchableOpacity style={styles.confirm}>
          <Text style={styles.confirmText}>Confirm Booking</Text>
        </TouchableOpacity>
      </View>

      {/* SERVICE MODAL */}
      <Modal visible={showService} transparent animationType="fade">
        <Pressable style={styles.overlay} onPress={() => setShowService(false)}>
          <View style={styles.menu}>
            {services.map(item => (
              <Pressable
                key={item}
                style={styles.menuItem}
                onPress={() => {
                  setService(item)
                  setShowService(false)
                }}
              >
                <Text>{item}</Text>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      {/* TIME MODAL */}
      <Modal visible={showTime} transparent animationType="fade">
        <Pressable style={styles.overlay} onPress={() => setShowTime(false)}>
          <View style={styles.menu}>
            {timeSlots.map(slot => (
              <Pressable
                key={slot}
                style={styles.menuItem}
                onPress={() => {
                  setTimeSlot(slot)
                  setShowTime(false)
                }}
              >
                <Text>{slot}</Text>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      {/* DATE PICKER */}
      {showDate && (
        <DateTimePicker
          value={date || new Date()}
          mode="date"
          display="default"
          onChange={(e, selectedDate) => {
            setShowDate(false)
            if (selectedDate) setDate(selectedDate)
          }}
        />
      )}
    </ScrollView>
  )
}

export default Book

const styles = StyleSheet.create({
  // Same as res_index
  container: {
    flex: 1,
    backgroundColor: '#0B3B91',
  },
  content: {
    paddingBottom: 32,
  },
  navbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingVertical: 16,
    backgroundColor: '#FFFFFF',
  },
  navLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  mainLogo: {
    width: 40,
    height: 40,
    borderRadius: 999,
  },
  partnerLogo: {
    width: 40,
    height: 40,
  },
  navLinks: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 24,
  },
  navLink: {
    fontSize: 22,
    color: '#1F2933',
    fontWeight: '500',
  },
  navLinkActive: {
    color: '#FBBF24',
  },
  logoutButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: '#1F3C88',
  },
  logoutText: {
    color: '#FF4D4D',
    fontSize: 22,
    fontWeight: '700',
  },
  heroSection: {
    paddingHorizontal: 24,
    paddingVertical: 40,
    backgroundColor: '#0B3B91',
    alignItems: 'center',
  },
  badge: {
    backgroundColor: '#FBBF24',
    paddingHorizontal: 25,
    paddingVertical: 8,
    borderRadius: 25,
    marginBottom: 15,
  },
  badgeText: { color: '#FFF', fontWeight: '700' },
  heroTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 12,
  },
  heroSubtitle: {
    fontSize: 20,
    color: '#E5E7EB',
    textAlign: 'center',
    marginBottom: 16,
    maxWidth: 640,
  },
  card: {
    marginHorizontal: 24,
    marginTop: 24,
    marginBottom: 32,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 8,
    elevation: 4,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  cardDivider: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 12,
  },

  row: { flexDirection: 'row', gap: 15, marginBottom: 15 },
  input: {
    flex: 1,
    backgroundColor: '#EAF2FB',
    borderRadius: 12,
    padding: 12,
  },

  label: { fontWeight: '600', marginBottom: 6 },
  dropdown: {
    backgroundColor: '#EAF2FB',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  dropText: { color: '#6B7280' },

  textArea: {
    backgroundColor: '#EAF2FB',
    borderRadius: 12,
    padding: 12,
    height: 100,
    marginVertical: 15,
    textAlignVertical: 'top',
  },

  priorityRow: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  priorityText: { flex: 1, fontSize: 14 },

  note: { fontSize: 12, color: '#6B7280', marginVertical: 10 },

  confirm: {
    backgroundColor: '#1F3C88',
    padding: 15,
    borderRadius: 12,
    marginTop: 15,
  },
  confirmText: {
    color: '#FFF',
    fontWeight: '700',
    textAlign: 'center',
    fontSize: 16,
  },

  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.25)',
    justifyContent: 'center',
    padding: 40,
  },

  menu: {
    backgroundColor: '#EAF2FB',
    borderRadius: 14,
    paddingVertical: 10,
  },

  menuItem: {
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#D1D5DB',
  },
})
