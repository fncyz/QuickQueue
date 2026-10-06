import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import { SafeAreaView } from 'react-native-safe-area-context';

import { QuickQueueLoadingIndicator } from '@/components/QuickQueueLoadingScreen';
import { Text } from '@/components/Typography';
import { useAppTheme } from '@/contexts/app-theme';
import { api } from '@/services/api';
import { readOfflineCache, writeOfflineCache } from '@/services/offline-cache';

type Pass = { id: number; booking_reference: string; qr_token: string; status: 'confirmed' | 'checked_in' | 'cancelled' | 'event_ended'; checked_in_at: string | null; resident_name: string; event_name: string; event_date: string; location: string };

export default function EventPassScreen() {
  const { colors, isDark } = useAppTheme();
  const { bookingId } = useLocalSearchParams<{ bookingId?: string }>();
  const [pass, setPass] = useState<Pass | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { let active = true; (async () => {
    const key = `eventPass.${bookingId}`;
    const cached = await readOfflineCache<Pass>(key); if (cached && active) setPass(cached.value);
    try { const token = await AsyncStorage.getItem('quickqueue.accessToken'); if (!token || !bookingId) throw new Error('Booking unavailable.'); const response = await api.get<Pass>(`event-bookings/${bookingId}/pass/`, { headers: { Authorization: `Bearer ${token}` } }); if (active) setPass(response.data); await writeOfflineCache(key, response.data); }
    catch (error: any) { if (!cached) Alert.alert('Unable to load QR Pass', error?.response?.data?.message || 'Please reconnect and try again.'); }
    finally { if (active) setLoading(false); }
  })(); return () => { active = false; }; }, [bookingId]);
  if (loading && !pass) return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]}><QuickQueueLoadingIndicator /></SafeAreaView>;
  if (!pass) return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]}><View style={s.empty}><Text style={{ color: colors.text }}>Event booking not found.</Text><Pressable onPress={() => router.back()} style={s.button}><Text style={s.buttonText}>Go Back</Text></Pressable></View></SafeAreaView>;
  const active = pass.status === 'confirmed';
  const statusLabel = pass.status === 'checked_in' ? 'Checked In' : pass.status === 'event_ended' ? 'Event Ended' : pass.status === 'cancelled' ? 'Cancelled' : 'Confirmed';
  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><View style={s.header}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable><Text style={s.headerTitle}>Event QR Pass</Text></View><ScrollView contentContainerStyle={s.content}><View style={[s.pass, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={s.eyebrow}>EVENT BOOKING CONFIRMED</Text><Text style={[s.title, { color: colors.text }]}>{pass.event_name}</Text><View style={[s.qrShell, !active && s.qrInactive]}><QRCode value={pass.qr_token} size={225} quietZone={10} color="#071A38" backgroundColor="#FFFFFF" ecl="H" />{!active && <View style={s.overlay}><Text style={s.overlayText}>{statusLabel.toUpperCase()}</Text></View>}</View><Text style={[s.scan, { color: colors.text }]}>{active ? 'Scan this QR code at the event venue' : pass.status === 'checked_in' ? 'This pass has already been used for check-in' : 'This pass is no longer valid for check-in'}</Text><Text style={[s.reference, isDark && { color: '#90BDF4' }]}>Booking Reference: {pass.booking_reference}</Text><View style={s.details}><Detail icon="person-outline" label="Resident Name" value={pass.resident_name} /><Detail icon="calendar-outline" label="Event Date" value={pass.event_date} /><Detail icon="location-outline" label="Location" value={pass.location || 'Not specified'} /></View><View style={[s.status, pass.status === 'cancelled' && s.cancelled, pass.status === 'event_ended' && s.ended]}><Ionicons name={pass.status === 'confirmed' ? 'checkmark-circle' : pass.status === 'checked_in' ? 'shield-checkmark' : 'information-circle'} size={20} color="#FFF" /><Text style={s.statusText}>{statusLabel}</Text></View>{pass.checked_in_at && <Text style={[s.checkedAt, { color: colors.muted }]}>Checked in {new Date(pass.checked_in_at).toLocaleString()}</Text>}</View></ScrollView></SafeAreaView>;
}

function Detail({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) { const { colors } = useAppTheme(); return <View style={s.detail}><Ionicons name={icon} size={18} color="#B65C00" /><View style={s.detailCopy}><Text style={[s.detailLabel, { color: colors.muted }]}>{label}</Text><Text style={[s.detailValue, { color: colors.text }]}>{value}</Text></View></View>; }
const s = StyleSheet.create({ safe: { flex: 1 }, header: { alignItems: 'center', backgroundColor: '#07419C', flexDirection: 'row', minHeight: 70, paddingHorizontal: 12 }, back: { padding: 10 }, headerTitle: { color: '#FFF', fontSize: 19, fontWeight: '800', marginLeft: 5 }, content: { alignItems: 'center', padding: 18, paddingBottom: 35 }, pass: { alignItems: 'center', borderRadius: 22, borderWidth: 1, maxWidth: 520, padding: 20, width: '100%' }, eyebrow: { color: '#A45A00', fontSize: 11, fontWeight: '900', letterSpacing: 1.2 }, title: { fontSize: 22, fontWeight: '800', lineHeight: 29, marginTop: 8, textAlign: 'center' }, qrShell: { backgroundColor: '#FFF', borderColor: '#E8B968', borderRadius: 18, borderWidth: 2, marginTop: 21, overflow: 'hidden', padding: 10, position: 'relative' }, qrInactive: { opacity: 0.72 }, overlay: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.9)', bottom: 80, left: 0, paddingVertical: 10, position: 'absolute', right: 0 }, overlayText: { color: '#A33B44', fontSize: 16, fontWeight: '900', letterSpacing: 1 }, scan: { fontSize: 13, fontWeight: '700', marginTop: 17, textAlign: 'center' }, reference: { color: '#0759D9', fontSize: 12, fontWeight: '800', marginTop: 8 }, details: { borderTopColor: '#E8EDF4', borderTopWidth: 1, marginTop: 19, width: '100%' }, detail: { alignItems: 'center', borderBottomColor: '#E8EDF4', borderBottomWidth: 1, flexDirection: 'row', minHeight: 58, paddingVertical: 9 }, detailCopy: { flex: 1, marginLeft: 11 }, detailLabel: { fontSize: 9 }, detailValue: { fontSize: 13, fontWeight: '600', marginTop: 2 }, status: { alignItems: 'center', backgroundColor: '#19965A', borderRadius: 20, flexDirection: 'row', gap: 7, marginTop: 20, paddingHorizontal: 18, paddingVertical: 10 }, cancelled: { backgroundColor: '#B63E49' }, ended: { backgroundColor: '#69778D' }, statusText: { color: '#FFF', fontSize: 13, fontWeight: '800' }, checkedAt: { fontSize: 10, marginTop: 9 }, button: { backgroundColor: '#0759D9', borderRadius: 9, marginTop: 16, paddingHorizontal: 18, paddingVertical: 11 }, buttonText: { color: '#FFF', fontWeight: '700' }, empty: { alignItems: 'center', flex: 1, justifyContent: 'center', padding: 25 } });
