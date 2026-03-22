import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import SideNavbar from './side_navbar'

const QUEUE_ITEMS = [
  {
    number: '1',
    badgeColor: '#BFDBFE',
    name: 'Maria Clara',
    service: 'Barangay Clearance',
    actions: [{ label: 'MARK SERVED', color: '#274C97' }],
  },
  {
    number: '2',
    badgeColor: '#BFDBFE',
    name: 'Juan Dela Cruz',
    service: 'Certificate of Residency',
    actions: [
      { label: 'Skip', color: '#ADADAD' },
      { label: 'MARK SERVED', color: '#274C97' },
    ],
  },
  {
    number: '1',
    badgeColor: '#F1BDF2',
    name: 'Pedro Ramos',
    service: 'Barangay Clearance',
    priority: 'Senior Citizen',
    actions: [{ label: 'Skip', color: '#ADADAD' }],
  },
]

const QueueManagementScreen = () => {
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
        <SideNavbar activeItem="Queue Management" />

        <View style={styles.contentPane}>
          <View style={[styles.headerRow, isMobile && styles.headerRowMobile]}>
            <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>Queue Management</Text>

            <View style={[styles.topActions, isMobile && styles.topActionsMobile]}>
              <TouchableOpacity activeOpacity={0.85} style={[styles.topActionButton, styles.nextButton]}>
                <Text style={styles.topActionText}>Call Next in Queue</Text>
              </TouchableOpacity>

              <TouchableOpacity activeOpacity={0.85} style={[styles.topActionButton, styles.priorityButton]}>
                <Text style={styles.topActionText}>Call Priority</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={[styles.queueList, isMobile && styles.queueListMobile]}>
            {QUEUE_ITEMS.map((item, index) => (
              <View key={`${item.name}-${index}`} style={[styles.queueCard, isMobile && styles.queueCardMobile]}>
                <View style={styles.queueInfo}>
                  <View style={[styles.numberBadge, { backgroundColor: item.badgeColor }]}>
                    <Text style={styles.numberText}>{item.number}</Text>
                  </View>

                  <View style={styles.textWrap}>
                    <Text style={styles.personName}>{item.name}</Text>
                    <Text style={styles.serviceText}>{item.service}</Text>
                    {item.priority ? <Text style={styles.priorityText}>{item.priority}</Text> : null}
                  </View>
                </View>

                <View style={[styles.cardActions, isMobile && styles.cardActionsMobile]}>
                  {item.actions.map((action) => (
                    <TouchableOpacity
                      key={action.label}
                      activeOpacity={0.85}
                      style={[
                        styles.cardButton,
                        { backgroundColor: action.color },
                        action.label === 'Skip' && styles.skipButton,
                      ]}
                    >
                      <Text style={styles.cardButtonText}>{action.label}</Text>
                    </TouchableOpacity>
                  ))}
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
  headerRow: {
    marginHorizontal: 72,
    marginBottom: 34,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 20,
  },
  headerRowMobile: {
    marginHorizontal: 0,
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
  headerTitle: {
    fontSize: 45,
    fontWeight: '800',
    color: '#CFE1F7',
  },
  headerTitleMobile: {
    fontSize: 36,
  },
  topActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 18,
  },
  topActionsMobile: {
    width: '100%',
    flexWrap: 'wrap',
  },
  topActionButton: {
    borderRadius: 18,
    paddingVertical: 20,
    paddingHorizontal: 34,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextButton: {
    backgroundColor: '#1AB100',
  },
  priorityButton: {
    backgroundColor: '#FF1208',
  },
  topActionText: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  queueList: {
    marginHorizontal: 68,
  },
  queueListMobile: {
    marginHorizontal: 0,
  },
  queueCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    paddingHorizontal: 26,
    paddingVertical: 24,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 18,
  },
  queueCardMobile: {
    flexDirection: 'column',
    alignItems: 'stretch',
  },
  queueInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  numberBadge: {
    width: 88,
    height: 94,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 28,
  },
  numberText: {
    fontSize: 28,
    fontWeight: '800',
    color: '#000000',
  },
  textWrap: {
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
  priorityText: {
    marginTop: 10,
    fontSize: 17,
    fontWeight: '700',
    color: '#FF1208',
  },
  cardActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 18,
  },
  cardActionsMobile: {
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
  },
  cardButton: {
    minWidth: 226,
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipButton: {
    minWidth: 200,
  },
  cardButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
})

export default QueueManagementScreen
