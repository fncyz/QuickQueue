import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';

type Appointment = { id: number; appointment_id: string; name: string; service: string; service_fee: string; date: string; time_slot: string; barangay: string; queue_number: string; now_serving: string; people_ahead: number; estimated_wait: number };

export default function QueueScreen() {
  const coverHeader = useCoverHeaderScroll();
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  const loadQueue = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) return router.replace('/login');
      setToken(accessToken);
      const response = await api.get('queue-status/', { headers: { Authorization: `Bearer ${accessToken}` } });
      setAppointment(response.data.appointment);
    } catch (error: any) {
      if (showLoader) Alert.alert('Unable to load queue', error?.response?.data?.message || 'Please check your connection.');
    } finally { if (showLoader) setLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => {
    loadQueue();
    const timer = setInterval(() => loadQueue(false), 15000);
    return () => clearInterval(timer);
  }, [loadQueue]));

  const performAction = async (action: 'check_in' | 'cancel') => {
    if (!appointment || acting) return;
    try {
      setActing(true);
      const response = await api.post('queue-status/', { appointment_id: appointment.id, action }, { headers: { Authorization: `Bearer ${token}` } });
      Alert.alert(action === 'check_in' ? 'Checked in' : 'Appointment cancelled', response.data.message);
      await loadQueue(false);
    } catch (error: any) {
      Alert.alert('Action unavailable', error?.response?.data?.message || 'Please try again.');
    } finally { setActing(false); }
  };

  const confirmCancellation = () => Alert.alert('Cancel appointment?', 'Your queue reservation will also be cancelled.', [
    { text: 'Keep Appointment', style: 'cancel' },
    { text: 'Cancel Appointment', style: 'destructive', onPress: () => performAction('cancel') },
  ]);

  if (loading) return <SafeAreaView style={s.loading}><ActivityIndicator size="large" color="#0646A8" /></SafeAreaView>;

  return <SafeAreaView style={[s.safe, { backgroundColor: '#FFFFFF' }]} edges={['top']}><Animated.ScrollView style={[s.page, { backgroundColor: '#FFFFFF' }]} contentContainerStyle={s.content} showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, coverHeader.headerStyle]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} /><View style={s.live}><View style={s.dot} /><Text style={s.liveText}>Live Status</Text></View><Text style={s.heading}>Current Queue Status</Text><Text style={s.subheading}>Track your queue in real time and stay ready for your turn.</Text></Animated.View>
    {!appointment ? <View style={s.empty}><Ionicons name="people-outline" size={48} color="#0759D9" /><Text style={s.emptyTitle}>No active appointment</Text><Text style={s.emptyCopy}>Book an appointment to view your live queue position here.</Text><Pressable onPress={() => router.push('/booking')} style={s.book}><Text style={s.bookText}>Book Now</Text></Pressable></View> : <>
      <View style={s.card}><SectionTitle icon="people-circle" title="Your Queue Status" subtitle="Real-time updates on your queue." right="You’re all set!" /><View style={s.ticketPanel}><Metric label="NOW SERVING" value={appointment.now_serving} icon="megaphone-outline" detail="Please proceed to the service counter." /><Metric label="YOUR NUMBER" value={appointment.queue_number} icon="person-outline" detail={appointment.people_ahead ? `${appointment.people_ahead} people ahead of you` : 'You are next in line'} center /><Metric label="ESTIMATED WAITING TIME" value={`${appointment.estimated_wait} minutes`} icon="time-outline" detail="Please wait for your turn." /></View><View style={s.note}><Ionicons name="notifications-outline" size={14} color="#0759D9" /><Text style={s.noteText}><Text style={s.noteStrong}>Note: </Text>Waiting time may change based on the number of people being served.</Text></View></View>
      <View style={s.card}><SectionTitle icon="flash" title="Appointment Actions" subtitle="Manage your appointment quickly and easily." /><View style={s.actions}><Pressable disabled={acting} onPress={() => performAction('check_in')} style={[s.action, s.check]}><Ionicons name="checkmark-circle" size={24} color="#22A950" /><View style={s.actionCopy}><Text style={s.checkTitle}>Check In</Text><Text style={s.actionText}>Let staff know you’ve arrived.</Text></View><Ionicons name="chevron-forward" size={17} color="#22A950" /></Pressable><Pressable disabled={acting} onPress={confirmCancellation} style={[s.action, s.cancel]}><Ionicons name="close-circle" size={24} color="#ED1C24" /><View style={s.actionCopy}><Text style={s.cancelTitle}>Cancel Appointment</Text><Text style={s.actionText}>Cancel if you cannot make it.</Text></View><Ionicons name="chevron-forward" size={17} color="#ED1C24" /></Pressable></View></View>
      <View style={s.card}><SectionTitle icon="calendar" title="Appointment Information" subtitle="Here are the details of your appointment." />{[
        ['document-text-outline', 'Appointment ID', appointment.appointment_id], ['person-outline', 'Name', appointment.name], ['briefcase-outline', 'Service', appointment.service], ['pricetag-outline', 'Service Fee', appointment.service_fee], ['calendar-outline', 'Date', appointment.date], ['time-outline', 'Time Slot', appointment.time_slot], ['location-outline', 'Barangay', appointment.barangay],
      ].map(([icon, label, value]) => <View key={label} style={s.detail}><Ionicons name={icon as keyof typeof Ionicons.glyphMap} size={14} color="#0759D9" /><Text style={s.detailLabel}>{label}</Text><Text style={s.detailValue}>{value}</Text></View>)}</View>
      <Pressable style={s.alert}><Ionicons name="notifications-outline" size={17} color="#0759D9" /><Text style={s.alertTitle}>System Alerts</Text><Text style={s.alertCopy}>Get notified when your queue status changes.</Text><Ionicons name="chevron-forward" size={17} color="#0759D9" /></Pressable>
    </>}
  </Animated.ScrollView></SafeAreaView>;
}

function SectionTitle({ icon, title, subtitle, right }: { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle: string; right?: string }) { return <View style={s.sectionHead}><View style={s.sectionIcon}><Ionicons name={icon} size={14} color="#FFF" /></View><View style={s.sectionCopy}><Text style={s.sectionTitle}>{title}</Text><Text style={s.sectionSubtitle}>{subtitle}</Text></View>{right && <Text style={s.ready}>✓ {right}</Text>}</View>; }
function Metric({ label, value, icon, detail, center }: { label: string; value: string; icon: keyof typeof Ionicons.glyphMap; detail: string; center?: boolean }) { return <View style={[s.metric, center && s.metricCenter]}><Text style={s.metricLabel}>{label}</Text><Text style={s.metricValue}>{value}</Text><Ionicons name={icon} size={19} color="#152654" /><Text style={s.metricDetail}>{detail}</Text></View>; }

const readableStyles = {
  liveText: { color: '#14B863', fontSize: 13 }, heading: { color: '#FFF', fontSize: 23, fontWeight: '800', marginTop: 9 }, subheading: { color: '#FFF', fontSize: 12, marginTop: 5 },
  sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 15, height: 30, justifyContent: 'center', marginRight: 8, width: 30 }, sectionTitle: { color: '#152654', fontSize: 14, fontWeight: '800' }, sectionSubtitle: { color: '#758096', fontSize: 10, marginTop: 2 }, ready: { color: '#0759D9', fontSize: 10, fontWeight: '700' },
  metric: { alignItems: 'center', flex: 1, minHeight: 125, paddingHorizontal: 6, paddingVertical: 13 }, metricLabel: { color: '#34415B', fontSize: 9, fontWeight: '700', textAlign: 'center' }, metricValue: { color: '#0646A8', fontSize: 21, fontWeight: '800', marginVertical: 7, textAlign: 'center' }, metricDetail: { color: '#34415B', fontSize: 9, fontWeight: '600', lineHeight: 12, marginTop: 6, textAlign: 'center' },
  noteText: { color: '#657089', flex: 1, fontSize: 10, lineHeight: 14 }, checkTitle: { color: '#1D9D4C', fontSize: 12, fontWeight: '800' }, cancelTitle: { color: '#E91E2B', fontSize: 12, fontWeight: '800' }, actionText: { color: '#667187', fontSize: 10, lineHeight: 13, marginTop: 3 },
  detail: { alignItems: 'center', borderBottomColor: '#E8ECF4', borderBottomWidth: 1, flexDirection: 'row', minHeight: 39 }, detailLabel: { color: '#34415B', fontSize: 11, marginLeft: 8, width: 88 }, detailValue: { color: '#152654', flex: 1, fontSize: 11, fontWeight: '700' }, alertTitle: { color: '#0759D9', fontSize: 12, fontWeight: '800' }, alertCopy: { color: '#657089', flex: 1, fontSize: 10 },
} as const;

const s = StyleSheet.create({
  safe: { backgroundColor: '#07419C', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#F7F9FD', flex: 1, justifyContent: 'center' }, page: { backgroundColor: '#F7F9FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', paddingBottom: 48, paddingTop: 55 }, back: { left: 18, padding: 8, position: 'absolute', top: 22 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 19, height: 38, justifyContent: 'center', position: 'absolute', right: 20, top: 31, width: 38 }, live: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 6, flexDirection: 'row', gap: 4, paddingHorizontal: 8, paddingVertical: 4 }, dot: { backgroundColor: '#14C76E', borderRadius: 4, height: 7, width: 7 }, liveText: { color: '#14B863', fontSize: 11 }, heading: { color: '#FFF', fontSize: 20, fontWeight: '800', marginTop: 9 }, subheading: { color: '#FFF', fontSize: 9, marginTop: 5 }, card: { backgroundColor: '#FFF', borderColor: '#E6EBF4', borderRadius: 15, borderWidth: 1, marginHorizontal: 7, marginTop: 9, padding: 12 }, cardFirst: { marginTop: -25 }, sectionHead: { alignItems: 'center', flexDirection: 'row', marginBottom: 9 }, sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 13, height: 26, justifyContent: 'center', marginRight: 7, width: 26 }, sectionCopy: { flex: 1 }, sectionTitle: { color: '#152654', fontSize: 10, fontWeight: '800' }, sectionSubtitle: { color: '#758096', fontSize: 7, marginTop: 1 }, ready: { color: '#0759D9', fontSize: 7, fontWeight: '700' }, ticketPanel: { backgroundColor: '#F4F7FD', borderRadius: 8, flexDirection: 'row', overflow: 'hidden' }, metric: { alignItems: 'center', flex: 1, minHeight: 104, paddingHorizontal: 5, paddingVertical: 11 }, metricCenter: { borderLeftColor: '#DCE4F2', borderLeftWidth: 1, borderRightColor: '#DCE4F2', borderRightWidth: 1 }, metricLabel: { color: '#34415B', fontSize: 6, fontWeight: '700', textAlign: 'center' }, metricValue: { color: '#0646A8', fontSize: 17, fontWeight: '800', marginVertical: 6, textAlign: 'center' }, metricDetail: { color: '#34415B', fontSize: 6, fontWeight: '600', lineHeight: 9, marginTop: 5, textAlign: 'center' }, note: { alignItems: 'center', backgroundColor: '#F1F5FD', borderRadius: 7, flexDirection: 'row', gap: 7, marginTop: 8, padding: 8 }, noteText: { color: '#657089', flex: 1, fontSize: 7 }, noteStrong: { color: '#0759D9', fontWeight: '800' }, actions: { flexDirection: 'row', gap: 7 }, action: { alignItems: 'center', borderRadius: 8, borderWidth: 1, flex: 1, flexDirection: 'row', minHeight: 58, padding: 8 }, check: { borderColor: '#79D49B' }, cancel: { borderColor: '#FF8D92' }, actionCopy: { flex: 1, marginLeft: 6 }, checkTitle: { color: '#1D9D4C', fontSize: 8, fontWeight: '800' }, cancelTitle: { color: '#E91E2B', fontSize: 8, fontWeight: '800' }, actionText: { color: '#667187', fontSize: 6, lineHeight: 9, marginTop: 3 }, detail: { alignItems: 'center', borderBottomColor: '#E8ECF4', borderBottomWidth: 1, flexDirection: 'row', minHeight: 30 }, detailLabel: { color: '#34415B', fontSize: 7, marginLeft: 7, width: 72 }, detailValue: { color: '#152654', flex: 1, fontSize: 7, fontWeight: '700' }, alert: { alignItems: 'center', backgroundColor: '#EEF4FF', borderRadius: 9, flexDirection: 'row', gap: 7, marginHorizontal: 7, marginTop: 9, padding: 11 }, alertTitle: { color: '#0759D9', fontSize: 8, fontWeight: '800' }, alertCopy: { color: '#657089', flex: 1, fontSize: 7 }, empty: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 16, marginHorizontal: 12, marginTop: -24, padding: 30 }, emptyTitle: { color: '#152654', fontSize: 17, fontWeight: '800', marginTop: 12 }, emptyCopy: { color: '#687189', fontSize: 11, marginTop: 6, textAlign: 'center' }, book: { backgroundColor: '#0646A8', borderRadius: 7, marginTop: 16, paddingHorizontal: 22, paddingVertical: 11 }, bookText: { color: '#FFF', fontSize: 11, fontWeight: '800' },
  ...(readableStyles as Record<string, object>),
});
