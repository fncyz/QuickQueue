import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Animated, Image, Pressable, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { useAppTheme } from '@/contexts/app-theme';
import { residentLayout } from '@/constants/resident-layout';

const quickQueueLogo = require('../assets/images/qq-logo.png');
const toledoLogo = require('../assets/images/toledo.png');
const cctcLogo = require('../assets/images/cctc.png');

type Service = { id: number; name: string };
type ActiveAppointment = {
  appointment_id: string;
  barangay: string;
  date: string;
  queue_number: string;
  service: string;
  status: string;
  status_code: string;
  time_slot: string;
};

const serviceIcon = (name: string): keyof typeof Ionicons.glyphMap => {
  const value = name.toLowerCase();
  if (value.includes('residency')) return 'home-outline';
  if (value.includes('indigency')) return 'person-outline';
  if (value.includes('business')) return 'briefcase-outline';
  if (value.includes('complaint')) return 'chatbubble-ellipses-outline';
  return 'document-text-outline';
};

export function ResidentDashboard() {
  const { colors, isDark } = useAppTheme();
  const coverHeader = useCoverHeaderScroll();
  const [residentName, setResidentName] = useState('Resident');
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [services, setServices] = useState<Service[]>([]);
  const [activeAppointment, setActiveAppointment] = useState<ActiveAppointment | null>(null);
  const [profilePhoto, setProfilePhoto] = useState<string | null>(null);
  const [serviceSearch, setServiceSearch] = useState('');
  const [showAllServices, setShowAllServices] = useState(false);

  useFocusEffect(useCallback(() => {
    let isActive = true;
    const loadDashboard = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return;
        const config = { headers: { Authorization: `Bearer ${accessToken}` } };
        const [profileResponse, notificationResponse, bookingResponse, queueResponse] = await Promise.all([
          api.get<{ username: string; first_name: string }>('profile/', config),
          api.get<{ unread_count: number }>('notifications/', config),
          api.get<{ services: Service[] }>('appointments/', config),
          api.get<{ appointment: ActiveAppointment | null }>('queue-status/', config),
        ]);
        if (!isActive) return;
        setResidentName(profileResponse.data.first_name);
        setUnreadNotifications(notificationResponse.data.unread_count);
        setServices(bookingResponse.data.services);
        setActiveAppointment(queueResponse.data.appointment);
        setProfilePhoto(await AsyncStorage.getItem(`quickqueue.profilePhoto.${profileResponse.data.username}`));
      } catch {
        // Keep the dashboard usable if fresh server data is temporarily unavailable.
      }
    };
    loadDashboard();
    return () => { isActive = false; };
  }, []));

  const filteredServices = useMemo(() => services.filter((item) => item.name.toLowerCase().includes(serviceSearch.trim().toLowerCase())), [serviceSearch, services]);
  const visibleServices = showAllServices || serviceSearch ? filteredServices : filteredServices.slice(0, 3);

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><Animated.ScrollView style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content} showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, coverHeader.headerStyle]}><View style={s.logos}><Image source={quickQueueLogo} style={s.brandLogo} resizeMode="contain" accessibilityLabel="QuickQueue logo" /><Image source={toledoLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="City of Toledo official seal" /><Image source={cctcLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="Consolatrix College of Toledo City logo" /></View><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} unreadCount={unreadNotifications} /><Pressable onPress={() => router.push('/profile')} style={s.headerProfile}>{profilePhoto ? <Image source={{ uri: profilePhoto }} style={s.headerProfileImage} /> : <Ionicons name="person" size={21} color="#0759D9" />}</Pressable><Text style={s.name}>Welcome back, {residentName}!</Text><Text style={s.subtitle}>Book your barangay appointment in just a few taps.</Text></Animated.View>
    {activeAppointment ? <UpcomingAppointmentCard appointment={activeAppointment} isDark={isDark} /> : <EmptyAppointmentCard isDark={isDark} />}
    <View style={[s.section, isDark && s.darkCard]}><View style={s.header}><Title icon="document-text" label="Available Services" /><Pressable onPress={() => setShowAllServices((value) => !value)}><Text style={[s.viewAll, { color: colors.accent }]}>{showAllServices ? 'Show Less' : 'View All  ›'}</Text></Pressable></View><View style={[s.search, isDark && s.darkIcon]}><Ionicons name="search" size={16} color={colors.muted} /><TextInput value={serviceSearch} onChangeText={setServiceSearch} placeholder="Search services" placeholderTextColor={colors.muted} style={[s.searchInput, { color: colors.text }]} /></View>{visibleServices.map((service) => <Pressable key={service.id} onPress={() => router.push({ pathname: '/booking', params: { serviceId: String(service.id) } })} style={[s.service, isDark && s.darkService]}><View style={[s.serviceIcon, isDark && s.darkIcon]}><Ionicons name={serviceIcon(service.name)} size={21} color={colors.accent} /></View><View style={{ flex: 1 }}><Text style={[s.serviceTitle, { color: colors.text }]}>{service.name}</Text><Text style={[s.serviceDetail, { color: colors.muted }]}>Book this service with your barangay.</Text></View><Ionicons name="chevron-forward" size={18} color={colors.accent} /></Pressable>)}</View>
    <View style={[s.section, isDark && s.darkCard]}><Title icon="time" label="Office Hours" /><Hours label="Monday – Friday" value="8:00 AM – 5:00 PM" /><Hours label="Saturday" value="8:00 AM – 12:00 PM" /><Hours label="Sunday & Holidays" value="Closed" closed /></View>
    <Pressable onPress={() => router.push('/queue')} style={s.notice}><Ionicons name="information-circle" size={21} color="#034AAE" /><View style={{ flex: 1 }}><Text style={s.noticeTitle}>Make sure to arrive 5 minutes before your time slot.</Text><Text style={s.noticeCopy}>Late arrivals may forfeit your appointment.</Text></View><Ionicons name="chevron-forward" size={18} color="#0759D9" /></Pressable>
  </Animated.ScrollView></SafeAreaView>;
}

function UpcomingAppointmentCard({ appointment, isDark }: { appointment: ActiveAppointment; isDark: boolean }) {
  const { colors } = useAppTheme();
  const parsedDate = new Date(appointment.date);
  const dateWithDay = Number.isNaN(parsedDate.getTime())
    ? appointment.date
    : parsedDate.toLocaleDateString('en-US', { day: 'numeric', month: 'long', weekday: 'long', year: 'numeric' });
  const viewStatus = () => router.push({
    pathname: '/booking-success',
    params: {
      appointmentDate: appointment.date,
      appointmentId: appointment.appointment_id,
      queueNumber: appointment.queue_number,
      service: appointment.service,
      status: appointment.status,
      statusCode: appointment.status_code,
      timeSlot: appointment.time_slot,
    },
  });

  return <View style={[s.appointment, s.upcomingCard, isDark && s.darkCard]}>
    <View style={s.upcomingHeader}><View style={s.upcomingTitleRow}><View style={s.miniCalendar}><Ionicons name="calendar" size={15} color="#FFF" /></View><Text style={[s.upcomingTitle, { color: colors.text }]}>Upcoming Appointment</Text></View><Pressable accessibilityRole="button" onPress={viewStatus} style={s.viewStatus}><Text style={[s.viewStatusText, { color: colors.accent }]}>View All</Text><Ionicons name="chevron-forward" size={16} color={colors.accent} /></Pressable></View>
    <View style={s.upcomingBody}><View style={[s.documentTile, isDark && s.darkIcon]}><Ionicons name="document-text-outline" size={45} color={colors.accent} /></View><View style={s.upcomingCopy}><Text style={[s.upcomingService, { color: colors.text }]}>{appointment.service}</Text><View style={s.detailRow}><Ionicons name="calendar-outline" size={15} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>{dateWithDay}</Text></View><View style={s.detailRow}><Ionicons name="time-outline" size={16} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>{appointment.time_slot}</Text></View><View style={s.detailRow}><Ionicons name="location" size={16} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>Barangay {appointment.barangay}, Toledo City</Text></View></View></View>
    <Pressable accessibilityRole="button" onPress={viewStatus} style={[s.appointmentNotice, isDark && s.darkIcon]}><Ionicons name="information-circle" size={18} color={colors.accent} /><Text numberOfLines={1} style={[s.appointmentNoticeText, { color: colors.accent }]}>Please be at the venue 5 minutes before your time slot.</Text><Ionicons name="chevron-forward" size={16} color={colors.accent} /></Pressable>
  </View>;
}

function EmptyAppointmentCard({ isDark }: { isDark: boolean }) {
  const { colors } = useAppTheme();
  return <View style={[s.appointment, s.emptyAppointment, isDark && s.darkCard]}>
    <View style={[s.emptyCalendar, isDark && s.darkIcon]}><Ionicons name="calendar" size={39} color={colors.accent} /></View>
    <View style={s.emptyCopy}><Text style={[s.emptyTitle, { color: colors.text }]}>No Appointment Yet</Text><Text style={[s.emptyText, { color: colors.muted }]}>You don&apos;t have any appointment scheduled.</Text><Pressable onPress={() => router.push('/booking')} style={s.book}><Ionicons name="calendar" size={16} color="#FFF" /><Text style={s.bookText}>Book an Appointment</Text></Pressable></View>
    <View style={s.emptyIllustration}><Ionicons name="clipboard-outline" size={72} color={isDark ? '#2A4266' : '#D8E6FD'} /><View style={s.clockBadge}><Ionicons name="time-outline" size={28} color={isDark ? '#5E7CA8' : '#AFC9F3'} /></View></View>
  </View>;
}

function Title({ icon, label }: { icon: keyof typeof Ionicons.glyphMap; label: string }) { const { colors } = useAppTheme(); return <View style={s.titleRow}><Ionicons name={icon} size={21} color={colors.accent} /><Text style={[s.sectionTitle, { color: colors.text }]}>{label}</Text></View>; }
function Hours({ label, value, closed = false }: { label: string; value: string; closed?: boolean }) { const { colors } = useAppTheme(); return <View style={s.hours}><Text style={[s.hourLabel, { color: colors.text }]}>{label}</Text><Text style={[s.hourValue, { color: colors.text }, closed && s.closed]}>{value}</Text></View>; }

const readableStyles = {
  hero: { ...residentLayout.header, minHeight: 205 },
  brandLogo: { height: 42, width: 42 },
  partnerLogo: { height: 36, width: 36 },
  greeting: { color: '#FFFFFF', fontSize: 19, fontWeight: '600', lineHeight: 25 },
  name: { color: '#FFFFFF', fontSize: 28, fontWeight: '800', lineHeight: 35, marginTop: 2 },
  subtitle: { color: '#FFFFFF', fontSize: 14, lineHeight: 20, marginTop: 7 },
  cardTitle: { color: '#14213A', fontSize: 16, fontWeight: '800' },
  cardCopy: { color: '#687189', fontSize: 13, lineHeight: 18, marginTop: 4 },
  bookText: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' },
  sectionTitle: { color: '#0346A8', fontSize: 15, fontWeight: '800' },
  viewAll: { color: '#0346A8', fontSize: 12, fontWeight: '700' },
  service: { alignItems: 'center', borderColor: '#E7EDF9', borderRadius: 7, borderWidth: 1, flexDirection: 'row', marginTop: 6, minHeight: 62, padding: 8 },
  serviceIcon: { alignItems: 'center', backgroundColor: '#F3F6FD', borderRadius: 7, height: 50, justifyContent: 'center', marginRight: 10, width: 52 },
  serviceTitle: { color: '#0648AA', fontSize: 13, fontWeight: '800' },
  serviceDetail: { color: '#4D5569', fontSize: 11, lineHeight: 15, marginTop: 2 },
  hourLabel: { color: '#2A3040', fontSize: 13 },
  hourValue: { color: '#2A3040', fontSize: 13, fontWeight: '700' },
  aiTitle: { color: '#4E28A0', fontSize: 14, fontWeight: '800' },
  aiCopy: { color: '#605078', fontSize: 11, lineHeight: 16, marginTop: 2 },
  bubbleText: { color: '#FFD738', fontSize: 14, fontWeight: '800' },
  noticeTitle: { color: '#0648AA', fontSize: 12, fontWeight: '800' },
  noticeCopy: { color: '#4E5A71', fontSize: 11, lineHeight: 15, marginTop: 2 },
  upcomingCard: { alignItems: 'stretch', flexDirection: 'column', padding: 14 },
  upcomingHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  upcomingTitleRow: { alignItems: 'center', flexDirection: 'row', gap: 9 },
  miniCalendar: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 15, height: 30, justifyContent: 'center', width: 30 },
  upcomingTitle: { fontSize: 16, fontWeight: '800' },
  viewStatus: { alignItems: 'center', flexDirection: 'row', gap: 2, paddingVertical: 6 },
  viewStatusText: { fontSize: 12, fontWeight: '800' },
  upcomingBody: { alignItems: 'center', flexDirection: 'row', marginTop: 12 },
  documentTile: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 17, height: 92, justifyContent: 'center', width: 92 },
  upcomingCopy: { flex: 1, marginLeft: 14 },
  upcomingService: { fontSize: 16, fontWeight: '800', marginBottom: 5 },
  detailRow: { alignItems: 'center', flexDirection: 'row', gap: 7, marginTop: 5 },
  detailText: { flex: 1, fontSize: 11, lineHeight: 15 },
  appointmentNotice: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 10, flexDirection: 'row', gap: 7, marginTop: 10, minHeight: 42, paddingHorizontal: 11 },
  appointmentNoticeText: { flex: 1, fontSize: 9, lineHeight: 14 },
  emptyAppointment: { minHeight: 156, padding: 17 },
  emptyCalendar: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 42, height: 84, justifyContent: 'center', marginRight: 16, width: 84 },
  emptyCopy: { flex: 1 },
  emptyTitle: { fontSize: 17, fontWeight: '800' },
  emptyText: { fontSize: 12, lineHeight: 18, marginTop: 5 },
  emptyIllustration: { alignItems: 'center', justifyContent: 'center', marginLeft: 8, width: 72 },
  clockBadge: { bottom: 13, position: 'absolute', right: 0 },
} as const;

const s = StyleSheet.create({
  safe: { backgroundColor: '#FFFFFF', flex: 1 }, page: { backgroundColor: '#FFFFFF', flex: 1 }, content: { paddingBottom: 24 }, logos: { alignItems: 'center', flexDirection: 'row', gap: 10, marginBottom: 13 }, avatar: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, height: 44, justifyContent: 'center', position: 'absolute', right: 20, top: 30, width: 44 }, notificationBadge: { alignItems: 'center', backgroundColor: '#EF3340', borderColor: '#FFFFFF', borderRadius: 8, borderWidth: 2, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 2, position: 'absolute', right: -2, top: -2 }, notificationBadgeText: { color: '#FFFFFF', fontSize: 8, fontWeight: '800' }, appointment: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#C9D9F8', borderRadius: 22, borderWidth: 2, flexDirection: 'row', marginHorizontal: 18, marginTop: -22, padding: 18 }, circle: { alignItems: 'center', backgroundColor: '#F0F5FF', borderRadius: 34, height: 68, justifyContent: 'center', marginRight: 16, width: 68 }, book: { alignItems: 'center', alignSelf: 'flex-start', backgroundColor: '#0346A8', borderRadius: 5, flexDirection: 'row', gap: 7, marginTop: 10, paddingHorizontal: 11, paddingVertical: 8 }, section: { backgroundColor: '#FFFFFF', borderColor: '#EDF0F7', borderRadius: 14, borderWidth: 1, marginHorizontal: 18, marginTop: 12, padding: 12 }, header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, titleRow: { alignItems: 'center', flexDirection: 'row', gap: 8 }, hours: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }, closed: { color: '#E33636' }, ai: { alignItems: 'center', backgroundColor: '#F3EBFF', borderRadius: 11, flexDirection: 'row', gap: 10, marginHorizontal: 18, marginTop: 12, padding: 12 }, bubble: { alignItems: 'center', backgroundColor: '#2E75D4', borderRadius: 24, height: 46, justifyContent: 'center', width: 46 }, notice: { alignItems: 'center', backgroundColor: '#E8F2FF', borderRadius: 8, flexDirection: 'row', gap: 8, marginHorizontal: 18, marginTop: 10, padding: 11 },
  headerProfile: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 19, height: 38, justifyContent: 'center', overflow: 'hidden', position: 'absolute', right: 72, top: 33, width: 38 }, headerProfileImage: { height: '100%', width: '100%' }, trackLabel: { fontSize: 9, fontWeight: '800', marginBottom: 3 }, search: { alignItems: 'center', backgroundColor: '#F3F6FD', borderRadius: 9, flexDirection: 'row', gap: 8, marginBottom: 5, minHeight: 40, paddingHorizontal: 11 }, searchInput: { flex: 1, fontSize: 11 },
  darkCard: { backgroundColor: '#131E30', borderColor: '#2A3A52' }, darkService: { borderColor: '#2A3A52' }, darkIcon: { backgroundColor: '#203553' },
  ...readableStyles,
  ...({
    avatar: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, height: 44, justifyContent: 'center', position: 'absolute', right: 72, top: 30, width: 44 },
    headerProfile: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 19, height: 38, justifyContent: 'center', overflow: 'hidden', position: 'absolute', right: 20, top: 33, width: 38 },
  } as Record<string, object>),
});
