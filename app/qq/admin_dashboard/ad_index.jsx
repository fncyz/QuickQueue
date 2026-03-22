import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  useWindowDimensions,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const STATS = [
  {
    value: '5',
    label: "Today's Appointments",
    iconPack: 'ion',
    icon: 'calendar-outline',
    tint: '#DBEAFE',
    iconColor: '#3B82F6',
  },
  {
    value: '3',
    label: 'Current Queue Count',
    iconPack: 'mc',
    icon: 'account-multiple-outline',
    tint: '#FFEDD5',
    iconColor: '#F97316',
  },
  {
    value: '1',
    label: 'No Shows Today',
    iconPack: 'feather',
    icon: 'x',
    tint: '#F3F4F6',
    iconColor: '#6B7280',
  },
  {
    value: '1',
    label: 'Priority for Verification',
    iconPack: 'mc',
    icon: 'alert-outline',
    tint: '#FEE2E2',
    iconColor: '#EF4444',
  },
  {
    value: '1',
    label: 'Completed Today',
    iconPack: 'mc',
    icon: 'check-circle-outline',
    tint: '#DCFCE7',
    iconColor: '#22C55E',
  },
]

const QUEUE_ROWS = [
  {
    number: '1',
    name: 'Maria Clara',
    service: 'Barangay Clearance',
    badgeColor: '#BFDBFE',
    status: 'SERVING',
    statusColor: '#0A8F08',
    action: 'MARK SERVED',
    actionColor: '#1D22FF',
  },
  {
    number: '2',
    name: 'Juan Dela Cruz',
    service: 'Certificate of Residency',
    badgeColor: '#FDBA4D',
    action: 'NEXT',
    actionColor: '#F8B24C',
  },
  {
    number: '3',
    name: 'Pedro Bautista',
    service: 'Certificate of Indigency',
    badgeColor: '#B9B5AE',
    action: 'WAITING',
    actionColor: '#A9A39B',
  },
]

const renderStatIcon = (item) => {
  if (item.iconPack === 'ion') {
    return <Ionicons name={item.icon} size={20} color={item.iconColor} />
  }

  if (item.iconPack === 'feather') {
    return <Feather name={item.icon} size={20} color={item.iconColor} />
  }

  return <MaterialCommunityIcons name={item.icon} size={20} color={item.iconColor} />
}

const AdminDashboard = () => {
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
        <SideNavbar activeItem="Dashboard" />

        <View style={styles.dashboardPane}>
          <View style={styles.heroBlock}>
            <Text style={[styles.heroTitle, isMobile && styles.heroTitleMobile]}>Dashboard</Text>
            <Text style={styles.heroSubtitle}>Real-time queue and appointment monitoring</Text>
          </View>

          <View style={styles.statsWrap}>
            {STATS.map((item) => (
              <View key={item.label} style={[styles.statCard, isMobile && styles.statCardMobile]}>
                <View style={styles.statValueRow}>
                  <View style={[styles.statIconWrap, { backgroundColor: item.tint }]}>{renderStatIcon(item)}</View>
                  <Text style={styles.statValue}>{item.value}</Text>
                </View>
                <Text style={styles.statLabel}>{item.label}</Text>
              </View>
            ))}
          </View>

          <View style={styles.monitorSection}>
            <Text style={[styles.monitorTitle, isMobile && styles.monitorTitleMobile]}>
              Real-Time Queue Monitor
            </Text>

            {QUEUE_ROWS.map((row, index) => (
              <View key={row.number} style={[styles.queueCard, index > 0 && styles.queueCardSpaced, isMobile && styles.queueCardMobile]}>
                <View style={[styles.queueLeft, isMobile && styles.queueLeftMobile]}>
                  <View style={[styles.queueNumberBadge, { backgroundColor: row.badgeColor }]}>
                    <Text style={styles.queueNumberText}>{row.number}</Text>
                  </View>

                  <View style={styles.queuePersonMeta}>
                    <Text style={styles.queueName}>{row.name}</Text>
                    <Text style={styles.queueService}>{row.service}</Text>
                  </View>
                </View>

                <View style={[styles.queueActions, isMobile && styles.queueActionsMobile]}>
                  {row.status ? (
                    <View style={[styles.statusPill, { backgroundColor: row.statusColor }]}>
                      <Text style={styles.statusText}>{row.status}</Text>
                    </View>
                  ) : null}

                  <TouchableOpacity
                    activeOpacity={0.85}
                    style={[styles.actionButton, { backgroundColor: row.actionColor }]}
                  >
                    <Text style={styles.actionButtonText}>{row.action}</Text>
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
  dashboardPane: {
    flex: 1,
    backgroundColor: '#284B97',
    paddingHorizontal: 28,
    paddingTop: 28,
    paddingBottom: 40,
  },
  heroBlock: {
    alignItems: 'center',
    marginBottom: 22,
  },
  heroTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  heroTitleMobile: {
    fontSize: 36,
  },
  heroSubtitle: {
    fontSize: 20,
    color: '#F3F4F6',
    textAlign: 'center',
    marginTop: 6,
    fontWeight: '500',
  },
  statsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 24,
  },
  statCard: {
    width: 262,
    minHeight: 136,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 28,
    paddingVertical: 18,
    justifyContent: 'space-between',
  },
  statCardMobile: {
    width: '100%',
  },
  statValueRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statIconWrap: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  statValue: {
    fontSize: 36,
    fontWeight: '800',
    color: '#000000',
  },
  statLabel: {
    fontSize: 17,
    color: '#6B6871',
    fontWeight: '500',
    marginTop: 18,
  },
  monitorSection: {
    marginTop: 56,
  },
  monitorTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 28,
  },
  monitorTitleMobile: {
    fontSize: 32,
  },
  queueCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  queueCardSpaced: {
    marginTop: 20,
  },
  queueCardMobile: {
    flexDirection: 'column',
    alignItems: 'stretch',
    gap: 14,
  },
  queueLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 18,
  },
  queueLeftMobile: {
    marginRight: 0,
  },
  queueNumberBadge: {
    width: 92,
    height: 52,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 18,
  },
  queueNumberText: {
    fontSize: 32,
    fontWeight: '800',
    color: '#000000',
  },
  queuePersonMeta: {
    flexShrink: 1,
  },
  queueName: {
    fontSize: 20,
    fontWeight: '800',
    color: '#000000',
  },
  queueService: {
    marginTop: 6,
    fontSize: 16,
    color: '#FF3A2F',
    fontWeight: '600',
  },
  queueActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
  },
  queueActionsMobile: {
    justifyContent: 'space-between',
  },
  statusPill: {
    minWidth: 220,
    borderRadius: 12,
    alignItems: 'center',
    paddingVertical: 13,
    paddingHorizontal: 20,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  actionButton: {
    minWidth: 198,
    borderRadius: 12,
    alignItems: 'center',
    paddingVertical: 13,
    paddingHorizontal: 20,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default AdminDashboard
