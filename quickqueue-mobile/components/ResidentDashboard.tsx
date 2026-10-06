import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Animated, Image, ImageBackground, NativeScrollEvent, NativeSyntheticEvent, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { SavedInformationBanner } from '@/components/SavedInformationBanner';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { useAppTheme } from '@/contexts/app-theme';
import { residentLayout } from '@/constants/resident-layout';
import { useConnectivity } from '@/contexts/connectivity';
import { readOfflineCache, setCurrentAccountId, writeOfflineCache } from '@/services/offline-cache';

const quickQueueLogo = require('../assets/images/qqlogo.png');
const toledoLogo = require('../assets/images/toledo.png');
const cctcLogo = require('../assets/images/cctc.png');
const servicesBackground = require('../assets/images/services_bg.png');

type Service = { id: number; name: string };
type TemporaryService = { id: number; name: string; description: string; type: string; location: string; event_start_date: string; event_end_date: string; booking_start_date: string; booking_end_date: string; status: 'active' | 'ending_soon' | 'upcoming' | 'fully_booked'; capacity: number | null; remaining_capacity: number | null; can_book: boolean; is_event: boolean; is_booked: boolean; event_booking_id: number | null };
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
type DashboardCache = { activeAppointment: ActiveAppointment | null; residentName: string; services: Service[]; temporaryServices?: TemporaryService[]; unreadNotifications: number; username: string };

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
  const { isOnline } = useConnectivity();
  const coverHeader = useCoverHeaderScroll();
  const [residentName, setResidentName] = useState('Resident');
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [services, setServices] = useState<Service[]>([]);
  const [temporaryServices, setTemporaryServices] = useState<TemporaryService[]>([]);
  const [activeAppointment, setActiveAppointment] = useState<ActiveAppointment | null>(null);
  const [profilePhoto, setProfilePhoto] = useState<string | null>(null);
  const [serviceSearch, setServiceSearch] = useState('');
  const [showAllServices, setShowAllServices] = useState(false);
  const lastFreshLoad = useRef(0);
  const loadInFlight = useRef(false);

  useFocusEffect(useCallback(() => {
    let isActive = true;
    const loadDashboard = async () => {
      if (loadInFlight.current) return;
      loadInFlight.current = true;
      try {
      const saved = await readOfflineCache<DashboardCache>('dashboard');
      if (saved && isActive) {
        setResidentName(saved.value.residentName); setUnreadNotifications(saved.value.unreadNotifications); setServices(saved.value.services); setTemporaryServices(saved.value.temporaryServices || []); setActiveAppointment(saved.value.activeAppointment);
        const cachedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${saved.value.username}`);
        if (cachedPhoto) setProfilePhoto(cachedPhoto);
      }
      if (!isOnline) return;
      if (Date.now() - lastFreshLoad.current < 30000) return;
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return;
        const config = { headers: { Authorization: `Bearer ${accessToken}` } };
        const [profileResponse, notificationResponse, bookingResponse, queueResponse] = await Promise.all([
          api.get<{ username: string; first_name: string }>('profile/?summary=1', config),
          api.get<{ unread_count: number }>('notifications/?summary=1', config),
          api.get<{ services: Service[]; temporary_services: TemporaryService[] }>('appointments/?summary=1', config),
          api.get<{ appointment: ActiveAppointment | null }>('queue-status/', config),
        ]);
        if (!isActive) return;
        setResidentName(profileResponse.data.first_name);
        setUnreadNotifications(notificationResponse.data.unread_count);
        setServices(bookingResponse.data.services);
        setTemporaryServices(bookingResponse.data.temporary_services || []);
        setActiveAppointment(queueResponse.data.appointment);
        lastFreshLoad.current = Date.now();
        const cachedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${profileResponse.data.username}`);
        if (cachedPhoto) setProfilePhoto(cachedPhoto);
        await setCurrentAccountId(profileResponse.data.username);
        await writeOfflineCache<DashboardCache>('dashboard', { activeAppointment: queueResponse.data.appointment, residentName: profileResponse.data.first_name, services: bookingResponse.data.services, temporaryServices: bookingResponse.data.temporary_services || [], unreadNotifications: notificationResponse.data.unread_count, username: profileResponse.data.username });
      } catch {
        // Keep the dashboard usable if fresh server data is temporarily unavailable.
      } finally {
        loadInFlight.current = false;
      }
    };
    loadDashboard();
    return () => { isActive = false; };
  }, [isOnline]));

  const filteredServices = useMemo(() => services.filter((item) => item.name.toLowerCase().includes(serviceSearch.trim().toLowerCase())), [serviceSearch, services]);
  const visibleServices = showAllServices || serviceSearch ? filteredServices : filteredServices.slice(0, 3);

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><Animated.ScrollView automaticallyAdjustKeyboardInsets style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content} keyboardDismissMode="on-drag" keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, coverHeader.headerStyle]}><View style={s.logos}><Image source={quickQueueLogo} style={s.brandLogo} resizeMode="contain" accessibilityLabel="QuickQueue logo" /><Image source={toledoLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="City of Toledo official seal" /><Image source={cctcLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="Consolatrix College of Toledo City logo" /></View><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} unreadCount={unreadNotifications} /><Pressable onPress={() => router.push('/profile')} style={s.headerProfile}>{profilePhoto ? <Image source={{ uri: profilePhoto }} style={s.headerProfileImage} /> : <Ionicons name="person" size={21} color="#0759D9" />}</Pressable><Text style={s.name}>Mabuhay, {residentName}!</Text><Text numberOfLines={2} style={s.subtitle}>Book your barangay appointment in just a few taps.</Text></Animated.View>
    <SavedInformationBanner />
    {activeAppointment ? <UpcomingAppointmentCard appointment={activeAppointment} isDark={isDark} /> : <EmptyAppointmentCard isDark={isDark} />}
    {temporaryServices.length > 0 && <EventCarousel events={temporaryServices} />}
    <View style={[s.section, isDark && s.darkCard]}><View style={s.header}><Title icon="document-text" label="Available Services" /><Pressable onPress={() => setShowAllServices((value) => !value)}><Text style={[s.viewAll, { color: colors.accent }]}>{showAllServices ? 'Show Less' : 'View All  ›'}</Text></Pressable></View><View style={[s.search, isDark && s.darkIcon]}><Ionicons name="search" size={16} color={colors.muted} /><TextInput value={serviceSearch} onChangeText={setServiceSearch} placeholder="Search services" placeholderTextColor={colors.muted} style={[s.searchInput, { color: colors.text }]} /></View>{visibleServices.map((service) => <Pressable key={service.id} onPress={() => router.push({ pathname: '/booking', params: { serviceId: String(service.id) } })} style={[s.service, isDark && s.darkService]}><View style={[s.serviceIcon, isDark && s.darkIcon]}><Ionicons name={serviceIcon(service.name)} size={21} color={colors.accent} /></View><View style={{ flex: 1 }}><Text style={[s.serviceTitle, { color: colors.text }]}>{service.name}</Text><Text style={[s.serviceDetail, { color: colors.muted }]}>Book this service with your barangay.</Text></View><Ionicons name="chevron-forward" size={18} color={colors.accent} /></Pressable>)}</View>
    <View style={[s.section, isDark && s.darkCard]}><Title icon="time" label="Office Hours" /><Hours label="Monday – Friday" value="8:00 AM – 5:00 PM" /><Hours label="Saturday" value="8:00 AM – 12:00 PM" /><Hours label="Sunday & Holidays" value="Closed" closed /></View>
    <Pressable onPress={() => router.push('/queue')} style={[s.notice, { backgroundColor: colors.surfaceAlt }]}><Ionicons name="information-circle" size={21} color={colors.accent} /><View style={{ flex: 1 }}><Text style={[s.noticeTitle, { color: colors.text }]}>Make sure to arrive 5 minutes before your time slot.</Text><Text style={[s.noticeCopy, { color: colors.muted }]}>Late arrivals may forfeit your appointment.</Text></View><Ionicons name="chevron-forward" size={18} color={colors.accent} /></Pressable>
  </Animated.ScrollView></SafeAreaView>;
}

function EventCarousel({ events }: { events: TemporaryService[] }) {
  const { colors, isDark } = useAppTheme();
  const { width } = useWindowDimensions();
  const [activeIndex, setActiveIndex] = useState(0);
  const cardWidth = Math.min(width * 0.92 - 24, 576);
  const interval = cardWidth + 10;
  const onScrollEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => setActiveIndex(Math.max(0, Math.min(events.length - 1, Math.round(event.nativeEvent.contentOffset.x / interval))));
  const formatRange = (item: TemporaryService) => {
    const start = new Date(`${item.event_start_date}T00:00:00`); const end = new Date(`${item.event_end_date}T00:00:00`);
    const options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' };
    const dateRange = start.toLocaleDateString('en-US', options) === end.toLocaleDateString('en-US', options) ? start.toLocaleDateString('en-US', options) : `${start.toLocaleDateString('en-US', options)} – ${end.toLocaleDateString('en-US', options)}`;
    return dateRange;
  };
  const open = (item: TemporaryService) => item.is_event && item.is_booked && item.event_booking_id
    ? router.push({ pathname: '/event-pass' as never, params: { bookingId: String(item.event_booking_id) } })
    : router.push({ pathname: '/event-details' as never, params: { event: JSON.stringify(item) } });
  return <View style={[s.eventSection, { backgroundColor: colors.surface, borderColor: colors.border }, isDark && s.darkCard]}>
    <View style={s.eventSectionHeader}><SpecialServicesTitle /><Pressable onPress={() => router.push('/booking')} hitSlop={8}><Text style={[s.viewAll, { color: colors.accent }]}>View All  ›</Text></Pressable></View>
    <Animated.ScrollView horizontal pagingEnabled={false} snapToInterval={interval} decelerationRate="fast" disableIntervalMomentum showsHorizontalScrollIndicator={false} contentContainerStyle={s.eventList} onMomentumScrollEnd={onScrollEnd}>
      {events.map((item) => <Pressable accessibilityRole="button" key={item.id} onPress={() => open(item)} style={[s.eventCard, { width: cardWidth }]}>
        <ImageBackground source={servicesBackground} resizeMode="cover" imageStyle={s.eventBackgroundImage} style={s.eventBackground}>
          <View style={[s.eventContentShade, isDark && s.eventContentShadeDark]}>
            <View style={s.eventBadges}><Text style={s.eventKind}>{item.type === 'Event' ? 'COMMUNITY EVENT' : 'COMMUNITY SERVICE'}</Text><Text style={[s.eventStatus, item.status === 'ending_soon' && s.eventEnding, item.is_booked && s.eventBooked]}>{item.is_booked ? 'BOOKED ✓' : item.status === 'active' ? 'AVAILABLE NOW' : item.status.replace('_', ' ').toUpperCase()}</Text>{item.remaining_capacity !== null && <Text style={s.eventCapacity}>{item.remaining_capacity} {item.remaining_capacity === 1 ? 'SLOT' : 'SLOTS'} LEFT</Text>}</View>
            <Text numberOfLines={2} style={[s.eventTitle, isDark && s.eventTextDark]}>{item.name}</Text><Text numberOfLines={2} style={[s.eventDescription, isDark && s.eventMutedDark]}>{item.description}</Text>
            <View style={s.eventDetails}><View style={s.eventMeta}><Ionicons name="calendar-outline" size={15} color={isDark ? '#8CBBF5' : '#0759D9'} /><View style={s.eventMetaCopy}><Text style={[s.eventMetaLabel, isDark && s.eventMutedDark]}>Schedule</Text><Text numberOfLines={2} style={[s.eventMetaText, isDark && s.eventTextDark]}>{formatRange(item)}</Text></View></View>{Boolean(item.location) && <View style={s.eventMeta}><Ionicons name="location-outline" size={15} color={isDark ? '#8CBBF5' : '#0759D9'} /><View style={s.eventMetaCopy}><Text style={[s.eventMetaLabel, isDark && s.eventMutedDark]}>Location</Text><Text numberOfLines={2} style={[s.eventMetaText, isDark && s.eventTextDark]}>{item.location}</Text></View></View>}</View>
            <LinearGradient colors={["#003B91", "#075BCF", "#0784FF"]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={s.eventAction}><Text style={s.eventActionText}>{item.is_booked ? 'VIEW QR PASS' : item.can_book ? 'BOOK NOW' : 'VIEW DETAILS'}</Text><Ionicons name={item.is_booked ? 'qr-code-outline' : 'arrow-forward'} size={14} color="#FFF" /></LinearGradient>
          </View>
        </ImageBackground>
      </Pressable>)}
    </Animated.ScrollView>
    {events.length > 1 && <View style={s.eventDots}>{events.map((item, index) => <View key={item.id} style={[s.eventDot, index === activeIndex && s.eventDotActive]} />)}</View>}
  </View>;
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
    <View style={s.upcomingBody}><View style={[s.documentTile, isDark && s.darkIcon]}><Ionicons name="document-text-outline" size={22} color={colors.accent} /></View><View style={s.upcomingCopy}><Text style={[s.upcomingService, { color: colors.text }]}>{appointment.service}</Text><View style={s.detailRow}><Ionicons name="calendar-outline" size={14} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>{dateWithDay}</Text></View><View style={s.detailRow}><Ionicons name="time-outline" size={14} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>{appointment.time_slot}</Text></View><View style={s.detailRow}><Ionicons name="location" size={14} color={colors.accent} /><Text style={[s.detailText, { color: colors.muted }]}>Barangay {appointment.barangay}, Toledo City</Text></View></View></View>
    <Pressable accessibilityRole="button" onPress={viewStatus} style={[s.appointmentNotice, isDark && s.darkIcon]}><Ionicons name="information-circle" size={18} color={colors.accent} /><Text style={[s.appointmentNoticeText, { color: colors.accent }]}>Please be at the venue 5 minutes before your time slot.</Text><Ionicons name="chevron-forward" size={16} color={colors.accent} /></Pressable>
  </View>;
}

function EmptyAppointmentCard({ isDark }: { isDark: boolean }) {
  const { colors } = useAppTheme();
  return <View style={[s.appointment, s.emptyAppointment, isDark && s.darkCard]}>
    <View style={[s.emptyCalendar, isDark && s.darkIcon]}><Ionicons name="calendar" size={22} color={colors.accent} /></View>
    <View style={s.emptyCopy}>
      <Text numberOfLines={2} style={[s.emptyTitle, { color: colors.text }]}>No Appointment Yet</Text>
      <Text style={[s.emptyText, { color: colors.muted }]}>You don&apos;t have any appointment scheduled.</Text>
      <Pressable onPress={() => router.push('/booking')} style={s.book}><Ionicons name="calendar-outline" size={16} color="#FFF" /><Text numberOfLines={2} style={s.bookText}>Book an Appointment</Text></Pressable>
    </View>
    <View style={s.emptyIllustration}><Ionicons name="clipboard-outline" size={32} color={isDark ? '#2A4266' : '#D8E6FD'} /><View style={s.clockBadge}><Ionicons name="time-outline" size={18} color={isDark ? '#5E7CA8' : '#AFC9F3'} /></View></View>
  </View>;
}

function Title({ icon, label }: { icon: keyof typeof Ionicons.glyphMap; label: string }) { const { colors } = useAppTheme(); return <View style={s.titleRow}><Ionicons name={icon} size={21} color={colors.accent} /><Text style={[s.sectionTitle, { color: colors.text }]}>{label}</Text></View>; }
function SpecialServicesTitle() { const { colors } = useAppTheme(); return <View style={s.titleRow}><View style={[s.specialServicesIcon, { backgroundColor: colors.accent }]}><MaterialCommunityIcons name="hand-heart" size={17} color="#FFF" /></View><Text style={[s.sectionTitle, { color: colors.text }]}>Special Services</Text></View>; }
function Hours({ label, value, closed = false }: { label: string; value: string; closed?: boolean }) { const { colors } = useAppTheme(); return <View style={s.hours}><Text style={[s.hourLabel, { color: colors.text }]}>{label}</Text><Text style={[s.hourValue, { color: colors.text }, closed && s.closed]}>{value}</Text></View>; }

const readableStyles = {
  hero: { ...residentLayout.header, minHeight: 205 },
  brandLogo: { height: 42, width: 42 },
  partnerLogo: { height: 36, width: 36 },
  greeting: { color: '#FFFFFF', fontSize: 19, fontWeight: '600', lineHeight: 25 },
  name: { color: '#FFFFFF', fontSize: 28, fontWeight: '800', lineHeight: 35, marginTop: 2 },
  subtitle: { color: '#FFFFFF', fontSize: 12, lineHeight: 18, marginTop: 7 },
  cardTitle: { color: '#14213A', fontSize: 15, fontWeight: '800' },
  cardCopy: { color: '#687189', fontSize: 13, lineHeight: 18, marginTop: 4 },
  bookText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700' },
  sectionTitle: { color: '#0346A8', fontSize: 15, fontWeight: '700' },
  viewAll: { color: '#0346A8', fontSize: 10, fontWeight: '600' },
  service: { alignItems: 'center', borderColor: '#E7EDF9', borderRadius: 7, borderWidth: 1, flexDirection: 'row', marginTop: 5, minHeight: 50, paddingHorizontal: 8, paddingVertical: 6 },
  serviceIcon: { alignItems: 'center', backgroundColor: '#F3F6FD', borderRadius: 7, height: 34, justifyContent: 'center', marginRight: 8, width: 34 },
  serviceTitle: { color: '#0648AA', fontSize: 13, fontWeight: '600' },
  serviceDetail: { color: '#4D5569', fontSize: 10, lineHeight: 16, marginTop: 1 },
  hourLabel: { color: '#2A3040', fontSize: 13 },
  hourValue: { color: '#2A3040', fontSize: 13, fontWeight: '600' },
  aiTitle: { color: '#4E28A0', fontSize: 14, fontWeight: '800' },
  aiCopy: { color: '#605078', fontSize: 11, lineHeight: 16, marginTop: 2 },
  bubbleText: { color: '#FFD738', fontSize: 14, fontWeight: '800' },
  noticeTitle: { color: '#0648AA', fontSize: 13, fontWeight: '600' },
  noticeCopy: { color: '#4E5A71', fontSize: 10, lineHeight: 16, marginTop: 1 },
  upcomingCard: { alignItems: 'stretch', flexDirection: 'column', padding: 12 },
  upcomingHeader: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'space-between' },
  upcomingTitleRow: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: 9, minWidth: 0 },
  miniCalendar: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 12, height: 24, justifyContent: 'center', width: 24 },
  upcomingTitle: { flexShrink: 1, fontSize: 14, fontWeight: '600' },
  viewStatus: { alignItems: 'center', flexDirection: 'row', gap: 2, minHeight: 36, paddingVertical: 4 },
  viewStatusText: { fontSize: 10, fontWeight: '600' },
  upcomingBody: { alignItems: 'center', flexDirection: 'row', marginTop: 8 },
  documentTile: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 12, height: 58, justifyContent: 'center', width: 58 },
  upcomingCopy: { flex: 1, marginLeft: 10, minWidth: 0 },
  upcomingService: { fontSize: 14, fontWeight: '600', marginBottom: 2 },
  detailRow: { alignItems: 'center', flexDirection: 'row', gap: 5, marginTop: 3 },
  detailText: { flex: 1, flexShrink: 1, fontSize: 10, lineHeight: 16, minWidth: 0 },
  appointmentNotice: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 8, flexDirection: 'row', gap: 6, marginTop: 8, minHeight: 36, paddingHorizontal: 9, paddingVertical: 5 },
  appointmentNoticeText: { flex: 1, fontSize: 10, lineHeight: 16 },
  emptyAppointment: { minHeight: 112, padding: 12 },
  emptyCalendar: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 25, height: 50, justifyContent: 'center', marginRight: 10, width: 50 },
  emptyCopy: { flex: 1, minWidth: 0 },
  emptyTitle: { flexShrink: 1, fontSize: 15, fontWeight: '600' },
  emptyText: { fontSize: 10, lineHeight: 16, marginTop: 2 },
  emptyIllustration: { alignItems: 'center', justifyContent: 'center', marginLeft: 4, width: 38 },
  clockBadge: { bottom: 8, position: 'absolute', right: -1 },
} as const;

const s = StyleSheet.create({
  safe: { backgroundColor: '#FFFFFF', flex: 1 }, page: { backgroundColor: '#FFFFFF', flex: 1 }, content: { paddingBottom: 24 }, logos: { alignItems: 'center', flexDirection: 'row', gap: 10, marginBottom: 13 }, avatar: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, height: 44, justifyContent: 'center', position: 'absolute', right: 20, top: 30, width: 44 }, notificationBadge: { alignItems: 'center', backgroundColor: '#EF3340', borderColor: '#FFFFFF', borderRadius: 8, borderWidth: 2, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 2, position: 'absolute', right: -2, top: -2 }, notificationBadgeText: { color: '#FFFFFF', fontSize: 8, fontWeight: '800' }, appointment: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#C9D9F8', borderRadius: 22, borderWidth: 2, flexDirection: 'row', marginHorizontal: 18, marginTop: -22, padding: 18 }, circle: { alignItems: 'center', backgroundColor: '#F0F5FF', borderRadius: 34, height: 68, justifyContent: 'center', marginRight: 16, width: 68 }, book: { alignItems: 'center', alignSelf: 'stretch', backgroundColor: '#0346A8', borderRadius: 5, flexDirection: 'row', gap: 7, justifyContent: 'center', marginTop: 9, paddingHorizontal: 8, paddingVertical: 8 }, section: { backgroundColor: '#FFFFFF', borderColor: '#EDF0F7', borderRadius: 14, borderWidth: 1, marginHorizontal: 18, marginTop: 12, padding: 12 }, header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, titleRow: { alignItems: 'center', flexDirection: 'row', gap: 8 }, specialServicesIcon: { alignItems: 'center', borderRadius: 12, height: 24, justifyContent: 'center', width: 24 }, hours: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }, closed: { color: '#E33636' }, ai: { alignItems: 'center', backgroundColor: '#F3EBFF', borderRadius: 11, flexDirection: 'row', gap: 10, marginHorizontal: 18, marginTop: 12, padding: 12 }, bubble: { alignItems: 'center', backgroundColor: '#2E75D4', borderRadius: 24, height: 46, justifyContent: 'center', width: 46 }, notice: { alignItems: 'center', backgroundColor: '#E8F2FF', borderRadius: 8, flexDirection: 'row', gap: 8, marginHorizontal: 18, marginTop: 10, padding: 11 },
  eventSection: { alignSelf: 'center', borderRadius: 18, borderWidth: 1, marginTop: 12, maxWidth: 600, overflow: 'hidden', paddingHorizontal: 12, paddingTop: 12, width: '92%' },
  eventSectionHeader: { alignItems: 'center', flexDirection: 'row', gap: 10, justifyContent: 'space-between', marginBottom: 10 },
  eventList: { gap: 10, paddingRight: 2 },
  eventCard: { borderRadius: 16, minHeight: 260, overflow: 'hidden' },
  eventBackground: { flex: 1, minHeight: 260 },
  eventBackgroundImage: { borderRadius: 16 },
  eventContentShade: { backgroundColor: 'rgba(239,247,255,0.88)', flex: 1, minHeight: 260, paddingBottom: 12, paddingHorizontal: 13, paddingTop: 10, width: '100%' },
  eventContentShadeDark: { backgroundColor: 'rgba(9,20,38,0.88)' },
  eventBadges: { alignItems: 'center', flexDirection: 'row', gap: 3, justifyContent: 'center', minWidth: 0 },
  eventKind: { backgroundColor: '#C9E4FF', borderRadius: 8, color: '#0759D9', flexShrink: 0, fontSize: 5, fontWeight: '500', paddingHorizontal: 5, paddingVertical: 3 },
  eventStatus: { backgroundColor: '#C8F0D5', borderRadius: 8, color: '#17713C', flexShrink: 0, fontSize: 5, fontWeight: '500', paddingHorizontal: 5, paddingVertical: 3 },
  eventCapacity: { backgroundColor: '#FFD5C3', borderRadius: 8, color: '#B84421', flexShrink: 0, fontSize: 5, fontWeight: '500', paddingHorizontal: 5, paddingVertical: 3 },
  eventEnding: { backgroundColor: '#FFF0D4', color: '#A85A00' }, eventBooked: { backgroundColor: '#E3EEFF', color: '#0759D9' },
  eventTitle: { color: '#10336C', fontSize: 20, fontWeight: '900', lineHeight: 25, marginTop: 8, textAlign: 'center' },
  eventDescription: { alignSelf: 'center', color: '#405574', fontSize: 11, lineHeight: 16, marginTop: 2, maxWidth: '94%', minHeight: 32, textAlign: 'center' },
  eventTextDark: { color: '#F4F7FC' }, eventMutedDark: { color: '#CAD6E6' },
  eventDetails: { alignSelf: 'center', gap: 4, marginTop: 6, width: '94%' }, eventMeta: { alignItems: 'flex-start', flexDirection: 'row', gap: 7, minHeight: 18 }, eventMetaCopy: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', gap: 4, minWidth: 0 }, eventMetaLabel: { color: '#607493', fontSize: 9, fontWeight: '600' }, eventMetaText: { color: '#254064', flexShrink: 1, fontSize: 9, fontWeight: '800', minWidth: 0 },
  eventAction: { alignItems: 'center', alignSelf: 'stretch', borderRadius: 10, flexDirection: 'row', gap: 6, justifyContent: 'center', marginTop: 'auto', minHeight: 38, paddingHorizontal: 13, paddingVertical: 8 }, eventActionText: { color: '#FFF', fontSize: 12, fontWeight: '900' },
  eventDots: { alignItems: 'center', flexDirection: 'row', gap: 5, justifyContent: 'center', minHeight: 24 }, eventDot: { backgroundColor: '#C8D5E7', borderRadius: 4, height: 7, width: 7 }, eventDotActive: { backgroundColor: '#0759D9', width: 13 },
  headerProfile: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 19, height: 38, justifyContent: 'center', overflow: 'hidden', position: 'absolute', right: 72, top: 33, width: 38 }, headerProfileImage: { height: '100%', width: '100%' }, trackLabel: { fontSize: 12, fontWeight: '600', marginBottom: 3 }, search: { alignItems: 'center', backgroundColor: '#F3F6FD', borderRadius: 9, flexDirection: 'row', gap: 8, marginBottom: 5, minHeight: 40, paddingHorizontal: 11 }, searchInput: { flex: 1, fontSize: 14 },
  darkCard: { backgroundColor: '#131E30', borderColor: '#2A3A52' }, darkService: { borderColor: '#2A3A52' }, darkIcon: { backgroundColor: '#203553' },
  ...readableStyles,
  ...({
    avatar: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, height: 44, justifyContent: 'center', position: 'absolute', right: 72, top: 30, width: 44 },
    headerProfile: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 19, height: 38, justifyContent: 'center', overflow: 'hidden', position: 'absolute', right: 20, top: 33, width: 38 },
    appointment: { alignItems: 'center', alignSelf: 'center', backgroundColor: '#FFFFFF', borderColor: '#C9D9F8', borderRadius: 18, borderWidth: 2, flexDirection: 'row', marginHorizontal: 0, marginTop: -22, maxWidth: 600, padding: 12, width: '92%' },
    section: { alignSelf: 'center', backgroundColor: '#FFFFFF', borderColor: '#EDF0F7', borderRadius: 14, borderWidth: 1, marginHorizontal: 0, marginTop: 10, maxWidth: 600, padding: 12, width: '92%' },
    notice: { alignItems: 'center', alignSelf: 'center', backgroundColor: '#E8F2FF', borderRadius: 8, flexDirection: 'row', gap: 8, marginHorizontal: 0, marginTop: 10, maxWidth: 600, padding: 11, width: '92%' },
    header: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'space-between', marginBottom: 8 },
    service: { alignItems: 'center', borderColor: '#E7EDF9', borderRadius: 7, borderWidth: 1, flexDirection: 'row', marginTop: 5, minHeight: 50, minWidth: 0, paddingHorizontal: 8, paddingVertical: 6 },
    hours: { alignItems: 'flex-start', flexDirection: 'row', gap: 12, justifyContent: 'space-between', marginTop: 12 },
    hourLabel: { color: '#2A3040', flex: 1, fontSize: 13, minWidth: 0 },
    hourValue: { color: '#2A3040', flexShrink: 1, fontSize: 13, fontWeight: '600', textAlign: 'right' },
  } as Record<string, object>),
});
