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
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* NAVBAR */}
      <View style={styles.navbar}>
        <View style={styles.navLeft}>
          <Image source={require('../../../assets/images/qq-logo.png')} style={styles.logo} />
          <Image source={require('../../../assets/images/toledo.png')} style={styles.logo} />
          <Image source={require('../../../assets/images/cctc.png')} style={styles.logo} />
        </View>

        <View style={styles.navLinks}>
          <TouchableOpacity onPress={() => router.push('/qq/res_dashboard/res_index')}>
            <Text style={styles.navLink}>Home</Text>
          </TouchableOpacity>
          <Text style={[styles.navLink, styles.active]}>Book Now</Text>
          <Text style={styles.navLink}>Queue Status</Text>
          <Text style={styles.navLink}>About</Text>
        </View>

        <TouchableOpacity
          style={styles.logout}
          onPress={() => router.replace('/qq/res_login')}
        >
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* HEADER */}
      <View style={styles.header}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>ONLINE BOOKING</Text>
        </View>
        <Text style={styles.title}>Schedule Your Appointment</Text>
        <Text style={styles.subtitle}>
          Book your visit in advance and skip the waiting room. Get instant confirmation
          and queue number.
        </Text>
      </View>

      {/* FORM */}
      <View style={styles.card}>
        <Text style={styles.section}>Personal Information</Text>

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
  container: { flex: 1, backgroundColor: '#24478F' },

  navbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: '#FFF',
    alignItems: 'center',
  },

  navLeft: { flexDirection: 'row', gap: 10 },
  logo: { width: 40, height: 40 },

  navLinks: { flexDirection: 'row', gap: 25 },
  navLink: { fontSize: 18, color: '#1F2933' },
  active: { color: '#FBBF24', fontWeight: '700' },

  logout: {
    backgroundColor: '#1F3C88',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 30,
  },
  logoutText: { color: '#FF4D4D', fontWeight: '700' },

  header: { alignItems: 'center', paddingVertical: 30 },
  badge: {
    backgroundColor: '#FBBF24',
    paddingHorizontal: 25,
    paddingVertical: 8,
    borderRadius: 25,
    marginBottom: 15,
  },
  badgeText: { color: '#FFF', fontWeight: '700' },
  title: { fontSize: 32, fontWeight: '800', color: '#DCE7FF' },
  subtitle: { color: '#E5E7EB', textAlign: 'center', maxWidth: 600 },

  card: {
    backgroundColor: '#FFF',
    marginHorizontal: 40,
    borderRadius: 15,
    padding: 25,
  },

  section: {
    textAlign: 'center',
    fontWeight: '700',
    fontSize: 18,
    marginBottom: 20,
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
