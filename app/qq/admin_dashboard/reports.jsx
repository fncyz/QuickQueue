import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import { MaterialCommunityIcons } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const TOP_SERVICES = [
  { name: 'Barangay Clearance', count: '10' },
  { name: 'Certificate of Residency', count: '7' },
  { name: 'Certificate of Indigency', count: '6' },
  { name: 'Business Permit', count: '3' },
  { name: 'Barangay ID', count: '2' },
]

const ReportsScreen = () => {
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
        <SideNavbar activeItem="Reports" />

        <View style={styles.contentPane}>
          <Text style={[styles.sectionTitle, isMobile && styles.sectionTitleMobile]}>Top Services</Text>

          <View style={[styles.summaryCard, isMobile && styles.summaryCardMobile]}>
            <View style={styles.summaryHeader}>
              <View>
                <Text style={styles.summaryLabel}>Total Served</Text>
                <Text style={[styles.summaryLabel, styles.summaryAccent]}>Average Wait Time</Text>
              </View>

              <View style={styles.summaryValues}>
                <Text style={styles.summaryValue}>28</Text>
                <Text style={styles.summaryValue}>10 mins</Text>
              </View>
            </View>

            <View style={styles.serviceTable}>
              {TOP_SERVICES.map((service, index) => (
                <View
                  key={service.name}
                  style={[styles.serviceRow, index % 2 === 0 ? styles.serviceRowBlue : styles.serviceRowWhite]}
                >
                  <Text style={styles.serviceName}>{service.name}</Text>
                  <Text style={styles.serviceCount}>{service.count}</Text>
                </View>
              ))}
            </View>
          </View>

          <Text style={[styles.sectionTitle, styles.ownerSectionTitle, isMobile && styles.sectionTitleMobile]}>
            Owner Verification Request
          </Text>

          <View style={[styles.ownerCard, isMobile && styles.ownerCardMobile]}>
            <View style={styles.ownerInfo}>
              <View style={styles.ownerIconTile}>
                <MaterialCommunityIcons name="account-outline" size={28} color="#2563EB" />
              </View>

              <View style={styles.ownerMeta}>
                <Text style={styles.ownerName}>KATARINA DELA CRUZ</Text>
                <Text style={styles.ownerEmail}>katarinadcruz@gmail.com</Text>
              </View>
            </View>

            <View style={[styles.ownerActions, isMobile && styles.ownerActionsMobile]}>
              <TouchableOpacity activeOpacity={0.85} style={[styles.ownerButton, styles.approveButton]}>
                <Text style={styles.ownerButtonText}>APPROVE</Text>
              </TouchableOpacity>

              <TouchableOpacity activeOpacity={0.85} style={[styles.ownerButton, styles.declineButton]}>
                <Text style={styles.ownerButtonText}>DECLINE</Text>
              </TouchableOpacity>
            </View>
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
  sectionTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
    marginHorizontal: 72,
    marginBottom: 24,
  },
  sectionTitleMobile: {
    fontSize: 36,
    marginHorizontal: 0,
  },
  summaryCard: {
    backgroundColor: '#1F3C78',
    borderRadius: 18,
    marginHorizontal: 46,
    paddingHorizontal: 26,
    paddingTop: 24,
    paddingBottom: 26,
  },
  summaryCardMobile: {
    marginHorizontal: 0,
  },
  summaryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 18,
  },
  summaryLabel: {
    fontSize: 22,
    fontWeight: '800',
    color: '#FFFFFF',
    lineHeight: 32,
  },
  summaryAccent: {
    color: '#F4C4FF',
  },
  summaryValues: {
    alignItems: 'flex-end',
  },
  summaryValue: {
    fontSize: 22,
    fontWeight: '800',
    color: '#FFFFFF',
    lineHeight: 32,
  },
  serviceTable: {
    overflow: 'hidden',
  },
  serviceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 56,
    minHeight: 50,
  },
  serviceRowBlue: {
    backgroundColor: '#9EC9F2',
  },
  serviceRowWhite: {
    backgroundColor: '#FFFFFF',
  },
  serviceName: {
    fontSize: 22,
    fontWeight: '500',
    color: '#000000',
  },
  serviceCount: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
  },
  ownerSectionTitle: {
    marginTop: 34,
  },
  ownerCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    marginHorizontal: 70,
    paddingHorizontal: 28,
    paddingVertical: 22,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 18,
  },
  ownerCardMobile: {
    marginHorizontal: 0,
    flexDirection: 'column',
    alignItems: 'stretch',
  },
  ownerInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  ownerIconTile: {
    width: 60,
    height: 60,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  ownerMeta: {
    flexShrink: 1,
  },
  ownerName: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
  },
  ownerEmail: {
    marginTop: 6,
    fontSize: 18,
    fontWeight: '700',
    color: '#274C97',
  },
  ownerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 18,
  },
  ownerActionsMobile: {
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
  },
  ownerButton: {
    minWidth: 244,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 24,
  },
  approveButton: {
    backgroundColor: '#18B100',
  },
  declineButton: {
    backgroundColor: '#FF1208',
  },
  ownerButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default ReportsScreen
