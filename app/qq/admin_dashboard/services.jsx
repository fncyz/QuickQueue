import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const SERVICE_CARDS = [
  {
    title: 'Barangay Clearance',
    processingTime: '1-2 days',
    fee: 'P50.00',
  },
  {
    title: 'Certificate of Residency',
    processingTime: 'Same day',
    fee: 'P30.00',
  },
  {
    title: 'Certificate of Indigency',
    processingTime: 'Same day',
    fee: 'P30.00',
  },
  {
    title: 'Barangay ID Application',
    processingTime: '1 week',
    fee: 'P100.00',
  },
  {
    title: 'Business Permit Application',
    processingTime: '3-5 days',
    fee: 'P2,000.00',
    featured: true,
  },
]

const OFFICE_HOURS = [
  { label: 'Monday - Friday', value: '8:00 AM - 5:00 PM' },
  { label: 'Saturday', value: '8:00 AM - 12:00 PM' },
  { label: 'Sunday & Holidays', value: 'Closed', closed: true },
]

const ServicesScreen = () => {
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
        <SideNavbar activeItem="Services" />

        <View style={styles.contentPane}>
          <View style={styles.headerBlock}>
            <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>Available Services</Text>
          </View>

          <View style={styles.cardsSection}>
            <View style={[styles.cardGrid, isMobile && styles.cardGridMobile]}>
              {SERVICE_CARDS.slice(0, 4).map((service) => (
                <View key={service.title} style={[styles.serviceCard, isMobile && styles.serviceCardMobile]}>
                  <Text style={styles.serviceTitle}>{service.title}</Text>
                  <Text style={styles.serviceMeta}>Processing Time: {service.processingTime}</Text>
                  <Text style={styles.serviceMeta}>Fee: {service.fee}</Text>
                </View>
              ))}
            </View>

            <View style={[styles.featuredCardWrap, isMobile && styles.featuredCardWrapMobile]}>
              <View style={[styles.serviceCard, styles.featuredCard, isMobile && styles.serviceCardMobile]}>
                <Text style={styles.serviceTitle}>{SERVICE_CARDS[4].title}</Text>
                <Text style={styles.serviceMeta}>Processing Time: {SERVICE_CARDS[4].processingTime}</Text>
                <Text style={styles.serviceMeta}>Fee: {SERVICE_CARDS[4].fee}</Text>
              </View>
            </View>
          </View>

          <View style={[styles.officeHoursCard, isMobile && styles.officeHoursCardMobile]}>
            <View style={styles.officeHeader}>
              <Feather name="clock" size={24} color="#6B7280" />
              <Text style={styles.officeTitle}>Office Hours</Text>
            </View>

            <View style={styles.officeList}>
              {OFFICE_HOURS.map((item) => (
                <View key={item.label} style={styles.officeRow}>
                  <Text style={styles.officeLabel}>{item.label}</Text>
                  <Text style={[styles.officeValue, item.closed && styles.officeValueClosed]}>{item.value}</Text>
                </View>
              ))}
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
  headerBlock: {
    marginHorizontal: 72,
    marginBottom: 28,
  },
  headerTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
  },
  headerTitleMobile: {
    fontSize: 36,
  },
  cardsSection: {
    marginHorizontal: 72,
  },
  cardGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 26,
  },
  cardGridMobile: {
    flexDirection: 'column',
  },
  serviceCard: {
    width: '46.5%',
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    paddingHorizontal: 34,
    paddingVertical: 18,
  },
  serviceCardMobile: {
    width: '100%',
  },
  featuredCardWrap: {
    alignItems: 'center',
    marginTop: 26,
  },
  featuredCardWrapMobile: {
    alignItems: 'stretch',
  },
  featuredCard: {
    width: '52%',
  },
  serviceTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
    marginBottom: 8,
  },
  serviceMeta: {
    fontSize: 17,
    color: '#111111',
    fontWeight: '400',
    lineHeight: 24,
  },
  officeHoursCard: {
    marginTop: 34,
    marginHorizontal: 112,
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    paddingHorizontal: 24,
    paddingVertical: 26,
  },
  officeHoursCardMobile: {
    marginHorizontal: 0,
  },
  officeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 28,
  },
  officeTitle: {
    marginLeft: 10,
    fontSize: 18,
    fontWeight: '800',
    color: '#111111',
  },
  officeList: {
    gap: 18,
  },
  officeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  officeLabel: {
    fontSize: 17,
    color: '#111111',
    fontWeight: '400',
  },
  officeValue: {
    fontSize: 17,
    color: '#111111',
    fontWeight: '700',
  },
  officeValueClosed: {
    color: '#EF4444',
  },
})

export default ServicesScreen
