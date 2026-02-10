import { ScrollView, View, Text, StyleSheet, Image, TouchableOpacity } from 'react-native'
import { useRouter } from 'expo-router'
import { Ionicons, MaterialIcons } from '@expo/vector-icons'

const ResidentHome = () => {
  const router = useRouter()

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top navigation bar */}
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
            <Text style={[styles.navLink, styles.navLinkActive]}>Home</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              router.push('/qq/res_dashboard/book')
            }}
          >
            <Text style={styles.navLink}>Book Now</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              router.push('/qq/res_dashboard/queue')
            }}
          >
            <Text style={styles.navLink}>Queue Status</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              // TODO: router.push('/qq/res_dashboard/about') when page exists
            }}
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

      {/* Hero section */}
      <View style={styles.heroSection}>
        <Text style={styles.heroTitle}>QuickQueue: Smart{"\n"}Appointments</Text>
        <Text style={styles.heroSubtitle}>
          Faster Lines. Smarter Appointments. Better Service.
        </Text>
        <Text style={styles.heroDescription}>
          A digital queue management system designed for barangays. Book appointments online,
          monitor queues in real time, and view estimated waiting times.
        </Text>

        <View style={styles.heroButtons}>
          <TouchableOpacity
            style={[styles.ctaButton, styles.bookButton]}
            onPress={() => {
              router.push('/qq/res_dashboard/book')
            }}
          >
            <Ionicons name="calendar" size={20} color="#0B3B91" style={styles.ctaIcon} />
            <Text style={[styles.ctaText, styles.bookText]}>Book Appointment</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.ctaButton, styles.queueButton]}
            onPress={() => {
              // Navigate to queue status page when available
            }}
          >
            <Ionicons name="eye" size={20} color="#FFFFFF" style={styles.ctaIcon} />
            <Text style={styles.ctaText}>View Queue</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Office hours card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Office Hours</Text>
        <View style={styles.cardDivider} />

        <View style={styles.hoursRow}>
          <View style={styles.hoursLabelColumn}>
            <Text style={styles.hoursLabel}>Monday - Friday</Text>
            <Text style={styles.hoursLabel}>Saturday</Text>
            <Text style={styles.hoursLabel}>Sunday & Holidays</Text>
          </View>
          <View style={styles.hoursValueColumn}>
            <Text style={styles.hoursValue}>8:00 AM - 5:00 PM</Text>
            <Text style={styles.hoursValue}>8:00 AM - 12:00 PM</Text>
            <Text style={[styles.hoursValue, styles.closedText]}>Closed</Text>
          </View>
        </View>
      </View>

      {/* AI wait prediction card */}
      <View style={[styles.card, styles.predictionCard]}>
        <View style={styles.predictionHeader}>
          <MaterialIcons name="lightbulb-outline" size={24} color="#F59E0B" />
          <Text style={styles.cardTitle}>AI Wait Prediction</Text>
        </View>
        <View style={styles.cardDivider} />
        <Text style={styles.predictionText}>
          Based on historical data, we predict shorter wait times on ----- and ----- between --- AM
          - PM.
        </Text>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
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
  },
  heroDescription: {
    fontSize: 16,
    color: '#E5E7EB',
    textAlign: 'center',
    maxWidth: 640,
  },
  heroButtons: {
    flexDirection: 'row',
    marginTop: 28,
    gap: 16,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  ctaButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 999,
  },
  bookButton: {
    backgroundColor: '#FBBF24',
  },
  queueButton: {
    backgroundColor: '#60A5FA',
  },
  ctaIcon: {
    marginRight: 8,
  },
  ctaText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  bookText: {
    color: '#0B3B91',
  },
  card: {
    marginHorizontal: 24,
    marginTop: 24,
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
  hoursRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  hoursLabelColumn: {
    gap: 8,
  },
  hoursValueColumn: {
    alignItems: 'flex-end',
    gap: 8,
  },
  hoursLabel: {
    fontSize: 17,
    color: '#4B5563',
  },
  hoursValue: {
    fontSize: 17,
    color: '#111827',
    fontWeight: '500',
  },
  closedText: {
    color: '#EF4444',
    fontWeight: '700',
  },
  predictionCard: {
    marginBottom: 32,
  },
  predictionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  predictionText: {
    fontSize: 17,
    color: '#4B5563',
  },
})

export default ResidentHome

