import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Animated, Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';

const quickQueueLogo = require('../assets/images/qq-logo.png');
const toledoLogo = require('../assets/images/toledo.png');
const cctcLogo = require('../assets/images/cctc.png');

const services = [
  ['document-text-outline', 'Barangay Clearance', 'Certificate for legal purposes and official transactions.'], ['home-outline', 'Certificate of Residency', 'Proof of residency for various transactions.'], ['person-outline', 'Certificate of Indigency', 'For low-income individuals needing financial assistance.'], ['briefcase-outline', 'Business Permit', 'Permit to operate or renew your business.'], ['chatbubble-ellipses-outline', 'File a Complaint', 'Submit a complaint or concern to the barangay.'],
] as const;

export function ResidentDashboard() {
  const coverHeader = useCoverHeaderScroll();
  const [residentName, setResidentName] = useState('Resident');
  const [unreadNotifications, setUnreadNotifications] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadResidentName = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return;

        const response = await api.get<{
          first_name: string;
          middle_name?: string;
          last_name: string;
          suffix?: string;
        }>('profile/', { headers: { Authorization: `Bearer ${accessToken}` } });

        if (!isMounted) return;
        const { first_name, middle_name, last_name, suffix } = response.data;
        const middleInitial = middle_name?.trim() ? `${middle_name.trim().charAt(0).toUpperCase()}.` : '';
        setResidentName([first_name, middleInitial, last_name, suffix].filter(Boolean).join(' '));
      } catch {
        // Keep the neutral fallback when the saved session cannot load a profile.
      }
    };

    loadResidentName();
    return () => { isMounted = false; };
  }, []);

  useFocusEffect(useCallback(() => {
    let isActive = true;
    const loadUnreadNotifications = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return;
        const response = await api.get<{ unread_count: number }>('notifications/', { headers: { Authorization: `Bearer ${accessToken}` } });
        if (isActive) setUnreadNotifications(response.data.unread_count);
      } catch {
        // Keep the bell usable if notification data is temporarily unavailable.
      }
    };
    loadUnreadNotifications();
    return () => { isActive = false; };
  }, []));

  return <SafeAreaView style={s.safe} edges={['top']}><Animated.ScrollView style={s.page} contentContainerStyle={s.content} showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, coverHeader.headerStyle]}><View style={s.logos}><Image source={quickQueueLogo} style={s.brandLogo} resizeMode="contain" accessibilityLabel="QuickQueue logo" /><Image source={toledoLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="City of Toledo official seal" /><Image source={cctcLogo} style={s.partnerLogo} resizeMode="contain" accessibilityLabel="Consolatrix College of Toledo City logo" /></View><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} unreadCount={unreadNotifications} /><Text style={s.greeting}>Mabuhay,</Text><Text style={s.name}>{residentName}!</Text><Text style={s.subtitle}>Book your barangay appointment in just a few taps.</Text></Animated.View>
    <View style={s.appointment}><View style={s.circle}><Ionicons name="calendar-outline" size={30} color="#0759D9" /></View><View style={{ flex: 1 }}><Text style={s.cardTitle}>No Appointment Yet</Text><Text style={s.cardCopy}>You don’t have any appointment scheduled.</Text><Pressable onPress={() => router.push('/booking')} style={s.book}><Ionicons name="calendar" size={14} color="#FFF" /><Text style={s.bookText}>Book an Appointment</Text></Pressable></View></View>
    <View style={s.section}><View style={s.header}><Title icon="document-text" label="Available Services" /><Pressable onPress={() => router.push('/booking')}><Text style={s.viewAll}>View All  ›</Text></Pressable></View>{services.map(([icon, title, detail]) => <Pressable key={title} onPress={() => router.push('/booking')} style={s.service}><View style={s.serviceIcon}><Ionicons name={icon} size={21} color="#0759D9" /></View><View style={{ flex: 1 }}><Text style={s.serviceTitle}>{title}</Text><Text style={s.serviceDetail}>{detail}</Text></View><Ionicons name="chevron-forward" size={18} color="#0759D9" /></Pressable>)}</View>
    <View style={s.section}><Title icon="time" label="Office Hours" /><Hours label="Monday – Friday" value="8:00 AM – 5:00 PM" /><Hours label="Saturday" value="8:00 AM – 12:00 PM" /><Hours label="Sunday & Holidays" value="Closed" closed /></View>
    <View style={s.ai}><Ionicons name="sparkles" size={24} color="#5B32B8" /><View style={{ flex: 1 }}><Text style={s.aiTitle}>AI Wait Prediction</Text><Text style={s.aiCopy}>Based on historical data, expected wait time after is around 10 – 15 mins.</Text></View><View style={s.bubble}><Text style={s.bubbleText}>QQ</Text></View></View>
    <Pressable onPress={() => router.push('/queue')} style={s.notice}><Ionicons name="information-circle" size={21} color="#034AAE" /><View style={{ flex: 1 }}><Text style={s.noticeTitle}>Make sure to arrive 5 minutes before your time slot.</Text><Text style={s.noticeCopy}>Late arrivals may forfeit your appointment.</Text></View><Ionicons name="chevron-forward" size={18} color="#0759D9" /></Pressable>
  </Animated.ScrollView></SafeAreaView>;
}

function Title({ icon, label }: { icon: keyof typeof Ionicons.glyphMap; label: string }) { return <View style={s.titleRow}><Ionicons name={icon} size={21} color="#0045AA" /><Text style={s.sectionTitle}>{label}</Text></View>; }
function Hours({ label, value, closed = false }: { label: string; value: string; closed?: boolean }) { return <View style={s.hours}><Text style={s.hourLabel}>{label}</Text><Text style={[s.hourValue, closed && s.closed]}>{value}</Text></View>; }

const readableStyles = {
  hero: { backgroundColor: '#07419C', minHeight: 205, padding: 20, paddingTop: 12 },
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
} as const;

const s = StyleSheet.create({
  safe: { backgroundColor: '#FFFFFF', flex: 1 }, page: { backgroundColor: '#FFFFFF', flex: 1 }, content: { paddingBottom: 24 }, logos: { alignItems: 'center', flexDirection: 'row', gap: 10, marginBottom: 13 }, avatar: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 22, height: 44, justifyContent: 'center', position: 'absolute', right: 20, top: 30, width: 44 }, notificationBadge: { alignItems: 'center', backgroundColor: '#EF3340', borderColor: '#FFFFFF', borderRadius: 8, borderWidth: 2, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 2, position: 'absolute', right: -2, top: -2 }, notificationBadgeText: { color: '#FFFFFF', fontSize: 8, fontWeight: '800' }, appointment: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#C9D9F8', borderRadius: 22, borderWidth: 2, flexDirection: 'row', marginHorizontal: 18, marginTop: -22, padding: 18 }, circle: { alignItems: 'center', backgroundColor: '#F0F5FF', borderRadius: 34, height: 68, justifyContent: 'center', marginRight: 16, width: 68 }, book: { alignItems: 'center', alignSelf: 'flex-start', backgroundColor: '#0346A8', borderRadius: 5, flexDirection: 'row', gap: 7, marginTop: 10, paddingHorizontal: 11, paddingVertical: 8 }, section: { backgroundColor: '#FFFFFF', borderColor: '#EDF0F7', borderRadius: 14, borderWidth: 1, marginHorizontal: 18, marginTop: 12, padding: 12 }, header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, titleRow: { alignItems: 'center', flexDirection: 'row', gap: 8 }, hours: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }, closed: { color: '#E33636' }, ai: { alignItems: 'center', backgroundColor: '#F3EBFF', borderRadius: 11, flexDirection: 'row', gap: 10, marginHorizontal: 18, marginTop: 12, padding: 12 }, bubble: { alignItems: 'center', backgroundColor: '#2E75D4', borderRadius: 24, height: 46, justifyContent: 'center', width: 46 }, notice: { alignItems: 'center', backgroundColor: '#E8F2FF', borderRadius: 8, flexDirection: 'row', gap: 8, marginHorizontal: 18, marginTop: 10, padding: 11 },
  ...readableStyles,
});
