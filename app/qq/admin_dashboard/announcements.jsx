import { ScrollView, View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import SideNavbar from './side_navbar'

const AnnouncementsScreen = () => {
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
        <SideNavbar activeItem="Announcements" />

        <View style={styles.contentPane}>
          <View style={[styles.headerRow, isMobile && styles.headerRowMobile]}>
            <Text style={[styles.headerTitle, isMobile && styles.headerTitleMobile]}>System Announcements</Text>

            <TouchableOpacity activeOpacity={0.85} style={[styles.addButton, isMobile && styles.addButtonMobile]}>
              <Text style={styles.addButtonText}>ADD NEW ANNOUNCEMENT</Text>
            </TouchableOpacity>
          </View>

          <View style={[styles.announcementCard, isMobile && styles.announcementCardMobile]}>
            <TouchableOpacity activeOpacity={0.85} style={styles.deleteButton}>
              <Feather name="trash-2" size={28} color="#B0B7C3" />
            </TouchableOpacity>

            <Text style={styles.announcementTitle}>Office Hours Extended</Text>
            <Text style={styles.announcementBody}>
              Office hours extended until 6:00 PM this week for faster processing.
            </Text>
            <Text style={styles.announcementDate}>2026-01-28</Text>

            <View style={styles.tagRow}>
              <View style={styles.importantTag}>
                <Text style={styles.importantTagText}>IMPORTANT</Text>
              </View>
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
  headerRow: {
    marginHorizontal: 60,
    marginBottom: 34,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  addButton: {
    backgroundColor: '#9EC9F2',
    borderRadius: 18,
    minHeight: 94,
    minWidth: 458,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  addButtonMobile: {
    minWidth: '100%',
  },
  addButtonText: {
    fontSize: 20,
    fontWeight: '800',
    color: '#000000',
  },
  announcementCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 136,
    paddingHorizontal: 26,
    paddingTop: 22,
    paddingBottom: 18,
    position: 'relative',
  },
  announcementCardMobile: {
    marginHorizontal: 0,
  },
  deleteButton: {
    position: 'absolute',
    top: 22,
    right: 24,
    zIndex: 1,
  },
  announcementTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
    marginBottom: 18,
    paddingRight: 56,
  },
  announcementBody: {
    fontSize: 17,
    color: '#000000',
    fontWeight: '400',
    lineHeight: 24,
    maxWidth: 860,
  },
  announcementDate: {
    marginTop: 16,
    fontSize: 17,
    fontWeight: '800',
    color: '#000000',
  },
  tagRow: {
    alignItems: 'flex-end',
    marginTop: -28,
  },
  importantTag: {
    backgroundColor: '#FFD45C',
    borderRadius: 16,
    minWidth: 260,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 20,
  },
  importantTagText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#000000',
  },
})

export default AnnouncementsScreen
