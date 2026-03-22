import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import { MaterialCommunityIcons } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const CALENDAR_COLUMNS = [
  { day: 'SUN', dates: ['', '4', '11', '18', '25'] },
  { day: 'MON', dates: ['', '5', '12', '19', '26'] },
  { day: 'TUE', dates: ['', '6', '13', '20', '27'] },
  { day: 'WED', dates: ['', '7', '14', '21', '28'] },
  { day: 'THU', dates: ['1', '8', '15', '22', '29'] },
  { day: 'FRI', dates: ['2', '9', '16', '23', '30'] },
  { day: 'SAT', dates: ['3', '10', '17', '24', '31'] },
]

const APPOINTMENTS = [
  {
    name: 'Maria Clara',
    service: 'Barangay Clearance',
    status: 'CONFIRMED',
    statusColor: '#81F780',
    statusTextColor: '#1D7A19',
    showConfirm: false,
  },
  {
    name: 'Juan Dela Cruz',
    service: 'Certificate of Residency',
    status: 'PENDING',
    statusColor: '#FFF200',
    statusTextColor: '#111111',
    showConfirm: true,
  },
]

const AppointmentsScreen = () => {
  const router = useRouter()
  const { width } = useWindowDimensions()
  const isCompact = width < 1100
  const isMobile = width < 760

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.screenContent}>
      <View style={styles.topBar}>
        <Text style={styles.topBarTitle}>Admin Panel</Text>
        <TouchableOpacity style={styles.logoutButton} onPress={() => router.replace('/qq/res_login')}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.mainLayout, isCompact && styles.mainLayoutStack]}>
        <SideNavbar activeItem="Appointments" />

        <View style={styles.contentPane}>
          <View style={styles.headerBlock}>
            <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>Appointment Calendar</Text>
            <Text style={styles.headerSubtitle}>Manage and view all appointments</Text>
          </View>

          <View style={styles.calendarCard}>
            <View style={[styles.calendarGrid, isMobile && styles.calendarGridMobile]}>
              {CALENDAR_COLUMNS.map((column) => (
                <View key={column.day} style={styles.calendarColumn}>
                  <Text style={styles.calendarDay}>{column.day}</Text>

                  {column.dates.map((date, index) => {
                    const isSelected = date === '29'

                    return (
                      <View key={`${column.day}-${index}`} style={styles.dateCell}>
                        <Text style={[styles.dateText, isSelected && styles.dateTextSelected]}>
                          {date}
                        </Text>
                      </View>
                    )
                  })}
                </View>
              ))}
            </View>
          </View>

          <Text style={[styles.sectionTitle, isMobile && styles.sectionTitleMobile]}>Today&apos;s Appointments</Text>

          <View style={styles.appointmentList}>
            {APPOINTMENTS.map((appointment) => (
              <View
                key={appointment.name}
                style={[styles.appointmentCard, isMobile && styles.appointmentCardMobile]}
              >
                <View style={styles.appointmentInfo}>
                  <View style={styles.iconTile}>
                    <MaterialCommunityIcons name="account-outline" size={34} color="#2563EB" />
                  </View>

                  <View style={styles.appointmentTextWrap}>
                    <Text style={styles.appointmentName}>{appointment.name}</Text>
                    <Text style={styles.appointmentService}>{appointment.service}</Text>
                  </View>
                </View>

                <View style={[styles.actionGroup, isMobile && styles.actionGroupMobile]}>
                  <View
                    style={[
                      styles.statusBadge,
                      { backgroundColor: appointment.statusColor },
                    ]}
                  >
                    <Text
                      style={[
                        styles.statusText,
                        { color: appointment.statusTextColor },
                      ]}
                    >
                      {appointment.status}
                    </Text>
                  </View>

                  {appointment.showConfirm ? (
                    <TouchableOpacity activeOpacity={0.85} style={[styles.actionButton, styles.confirmButton]}>
                      <Text style={styles.actionButtonText}>CONFIRM</Text>
                    </TouchableOpacity>
                  ) : null}

                  <TouchableOpacity activeOpacity={0.85} style={[styles.actionButton, styles.cancelButton]}>
                    <Text style={styles.actionButtonText}>CANCEL</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
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
    marginLeft: 64,
    marginBottom: 26,
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
    fontWeight: '500',
    color: '#F3F4F6',
    marginTop: 4,
  },
  calendarCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    paddingHorizontal: 28,
    paddingVertical: 26,
    marginHorizontal: 64,
  },
  calendarGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 20,
  },
  calendarGridMobile: {
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  calendarColumn: {
    flex: 1,
    alignItems: 'center',
    minWidth: 90,
  },
  calendarDay: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
    marginBottom: 8,
  },
  dateCell: {
    width: 106,
    height: 56,
    borderRadius: 16,
    backgroundColor: '#EDEDED',
    marginTop: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dateText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
  },
  dateTextSelected: {
    color: '#244C9A',
  },
  sectionTitle: {
    fontSize: 32,
    fontWeight: '800',
    color: '#CFE1F7',
    marginTop: 34,
    marginBottom: 18,
    marginLeft: 72,
  },
  sectionTitleMobile: {
    fontSize: 28,
    marginLeft: 0,
  },
  appointmentList: {
    marginHorizontal: 72,
  },
  appointmentCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    paddingHorizontal: 28,
    paddingVertical: 22,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 18,
  },
  appointmentCardMobile: {
    flexDirection: 'column',
    alignItems: 'stretch',
    gap: 16,
  },
  appointmentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 20,
  },
  iconTile: {
    width: 62,
    height: 62,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 24,
  },
  appointmentTextWrap: {
    flexShrink: 1,
  },
  appointmentName: {
    fontSize: 20,
    fontWeight: '800',
    color: '#000000',
  },
  appointmentService: {
    fontSize: 17,
    fontWeight: '700',
    color: '#244C9A',
    marginTop: 2,
  },
  actionGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 18,
  },
  actionGroupMobile: {
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
  },
  statusBadge: {
    minWidth: 240,
    borderRadius: 16,
    paddingVertical: 16,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  statusText: {
    fontSize: 16,
    fontWeight: '700',
  },
  actionButton: {
    minWidth: 240,
    borderRadius: 16,
    paddingVertical: 16,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  confirmButton: {
    backgroundColor: '#17A800',
  },
  cancelButton: {
    backgroundColor: '#FF1208',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default AppointmentsScreen
