import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import SideNavbar from './side_navbar'

const PriorityVerificationScreen = () => {
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
        <SideNavbar activeItem="Priority Verification" />

        <View style={styles.contentPane}>
          <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>
            Priority Verification Requests
          </Text>

          <View style={[styles.requestCard, isMobile && styles.requestCardMobile]}>
            <View style={styles.requestHeader}>
              <View style={styles.numberBadge}>
                <Text style={styles.numberText}>1</Text>
              </View>

              <View style={styles.personMeta}>
                <Text style={styles.personName}>Pedro Ramos</Text>
                <Text style={styles.serviceText}>Barangay Clearance</Text>
              </View>
            </View>

            <View style={styles.reasonPanel}>
              <Text style={styles.reasonLabel}>Reason for Priority:</Text>
              <Text style={styles.reasonText}>Senior Citizen (72 years old)</Text>
            </View>

            <View style={[styles.actionRow, isMobile && styles.actionRowMobile]}>
              <TouchableOpacity activeOpacity={0.85} style={[styles.actionButton, styles.acceptButton]}>
                <Text style={styles.actionButtonText}>Verify & Accept</Text>
              </TouchableOpacity>

              <TouchableOpacity activeOpacity={0.85} style={[styles.actionButton, styles.rejectButton]}>
                <Text style={styles.actionButtonText}>Reject</Text>
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
  headerTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
    marginHorizontal: 78,
    marginBottom: 34,
  },
  headerTitleMobile: {
    fontSize: 36,
    marginHorizontal: 0,
  },
  requestCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 120,
    paddingHorizontal: 28,
    paddingVertical: 28,
  },
  requestCardMobile: {
    marginHorizontal: 0,
  },
  requestHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  numberBadge: {
    width: 86,
    height: 96,
    borderRadius: 16,
    backgroundColor: '#F1BDF2',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 26,
  },
  numberText: {
    fontSize: 32,
    fontWeight: '800',
    color: '#000000',
  },
  personMeta: {
    flexShrink: 1,
  },
  personName: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
  },
  serviceText: {
    marginTop: 4,
    fontSize: 17,
    fontWeight: '700',
    color: '#274C97',
  },
  reasonPanel: {
    backgroundColor: '#BFDBFE',
    borderRadius: 18,
    marginTop: 24,
    marginLeft: 42,
    paddingHorizontal: 24,
    paddingVertical: 18,
  },
  reasonLabel: {
    fontSize: 18,
    fontWeight: '800',
    color: '#000000',
  },
  reasonText: {
    marginTop: 8,
    fontSize: 17,
    fontWeight: '400',
    color: '#000000',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 98,
    marginTop: 20,
  },
  actionRowMobile: {
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
    gap: 16,
  },
  actionButton: {
    minWidth: 368,
    borderRadius: 16,
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 24,
  },
  acceptButton: {
    backgroundColor: '#18B100',
  },
  rejectButton: {
    backgroundColor: '#FF1208',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default PriorityVerificationScreen
