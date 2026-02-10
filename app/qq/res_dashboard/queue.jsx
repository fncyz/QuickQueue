import React from 'react'
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
} from 'react-native'
import { useRouter } from 'expo-router'

const QueueStatus = () => {
  const router = useRouter()

  return (
    <ScrollView style={styles.container}>
      {/* NAVBAR */}
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
          <TouchableOpacity onPress={() => router.push('/qq/res_dashboard/res_index')}>
            <Text style={styles.navLink}>Home</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.push('/qq/res_dashboard/book')}>
            <Text style={styles.navLink}>Book Now</Text>
          </TouchableOpacity>

          <Text style={[styles.navLink, styles.navActive]}>Queue Status</Text>

          <Text style={styles.navLink}>About</Text>
        </View>

        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => router.replace('/qq/res_login')}
        >
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* HEADER */}
      <View style={styles.header}>
        <View style={styles.liveRow}>
          <View style={styles.liveBadge}>
            <Text style={styles.liveText}>LIVE STATUS</Text>
          </View>
          <View style={styles.dot} />
          <Text style={styles.updatedText}>Updated in real-time</Text>
        </View>

        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>Current Queue Status</Text>
            <Text style={styles.headerSubtitle}>
              Monitor all service queues and estimated wait times. Stay informed
              and plan your visit accordingly.
            </Text>
          </View>

          <View style={styles.bigNumber}>
            <Text style={styles.bigNumberText}>3</Text>
          </View>
        </View>
      </View>

      {/* SERVICE CARD */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle}>Barangay Clearance</Text>
          <View style={styles.nowServing}>
            <Text style={styles.nowServingText}>A-02</Text>
            <Text style={styles.nowServingLabel}>NOW SERVING</Text>
          </View>
        </View>

        <View style={styles.ticketRow}>
          <View style={styles.ticket}>
            <Text style={styles.ticketNumber}>A-02</Text>
            <Text style={styles.ticketSub}>Next - 3 mins</Text>
          </View>
          <View style={styles.ticket}>
            <Text style={styles.ticketNumber}>A-02</Text>
            <Text style={styles.ticketSub}>Next - 3 mins</Text>
          </View>
          <View style={styles.ticket}>
            <Text style={styles.ticketNumber}>A-02</Text>
            <Text style={styles.ticketSub}>Next - 3 mins</Text>
          </View>
        </View>

        <View style={styles.cardFooter}>
          <Text>Total waiting:</Text>
          <Text style={styles.bold}>5 people</Text>
        </View>
      </View>

      {/* PRIORITY QUEUE */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⭐ Priority Queue</Text>
        <Text style={styles.cardSub}>For elderly, PWD, pregnant</Text>

        <View style={styles.priorityBox}>
          <Text style={styles.priorityNumber}>1</Text>
          <Text>Priority cases waiting</Text>
        </View>

        <Text style={styles.note}>
          AI suggests priority handling. Staff verifies eligibility on arrival.
        </Text>
      </View>

      {/* TODAY OVERVIEW */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today’s Overview</Text>

        <View style={styles.overviewRow}>
          <Text>Total Served</Text>
          <Text style={styles.bold}>—</Text>
        </View>

        <View style={styles.overviewRow}>
          <Text>Currently waiting</Text>
          <Text style={styles.waiting}>3</Text>
        </View>

        <View style={styles.overviewRow}>
          <Text>Avg. Service Time</Text>
          <Text style={styles.time}>8 mins</Text>
        </View>
      </View>
    </ScrollView>
  )
}

export default QueueStatus

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B3B91',
  },

  navbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#FFFFFF',
  },

  navLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  mainLogo: { width: 40, height: 40, borderRadius: 20 },
  partnerLogo: { width: 40, height: 40 },

  navLinks: { flexDirection: 'row', gap: 24 },
  navLink: { fontSize: 18, color: '#1F2933' },
  navActive: { color: '#FBBF24', fontWeight: '700' },

  logoutButton: {
    backgroundColor: '#1F3C88',
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 999,
  },

  logoutText: {
    color: '#FF4D4D',
    fontWeight: '700',
    fontSize: 16,
  },

  header: {
    padding: 24,
  },

  liveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
  },

  liveBadge: {
    backgroundColor: '#16A34A',
    paddingHorizontal: 18,
    paddingVertical: 6,
    borderRadius: 999,
  },

  liveText: { color: '#FFFFFF', fontWeight: '700' },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#16A34A' },
  updatedText: { color: '#E5E7EB' },

  headerRow: { flexDirection: 'row', gap: 20 },
  headerTitle: { fontSize: 36, fontWeight: '800', color: '#FFFFFF' },
  headerSubtitle: { color: '#E5E7EB', marginTop: 8 },

  bigNumber: {
    backgroundColor: '#FCD34D',
    width: 90,
    height: 90,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },

  bigNumberText: { fontSize: 48, fontWeight: '800' },

  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    marginHorizontal: 24,
    marginBottom: 24,
    padding: 16,
  },

  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },

  cardTitle: { fontSize: 18, fontWeight: '700' },
  cardSub: { color: '#6B7280', marginBottom: 12 },

  ticketRow: { flexDirection: 'row', gap: 12, marginVertical: 12 },

  ticket: {
    backgroundColor: '#EAF2FB',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    flex: 1,
  },

  ticketNumber: { fontWeight: '800', fontSize: 16 },
  ticketSub: { color: '#6B7280', fontSize: 12 },

  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },

  nowServing: { alignItems: 'flex-end' },
  nowServingText: { fontWeight: '800' },
  nowServingLabel: { color: 'red', fontSize: 12 },

  priorityBox: {
    backgroundColor: '#E9D5FF',
    borderRadius: 12,
    padding: 16,
    marginVertical: 12,
  },

  priorityNumber: { fontSize: 28, fontWeight: '800' },

  note: { fontSize: 12, color: '#6B7280' },

  overviewRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },

  waiting: { color: 'red', fontWeight: '700' },
  time: { color: 'green', fontWeight: '700' },
  bold: { fontWeight: '700' },
})
