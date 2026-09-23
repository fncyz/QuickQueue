import AsyncStorage from '@react-native-async-storage/async-storage';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Picker } from '@react-native-picker/picker';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Animated, Platform, Pressable, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { residentLayout } from '@/constants/resident-layout';
import { useAppTheme } from '@/contexts/app-theme';

type Choice = { id: number; name?: string; label?: string };
type BookingProfile = {
  first_name: string;
  last_name: string;
  middle_name: string;
  suffix: string;
  birthdate: string;
  age: number;
  sex: string;
  address: string;
  barangay: string;
};

const formatDate = (value: Date | null) => value
  ? `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  : '';

export default function BookingScreen() {
  const { colors } = useAppTheme();
  const params = useLocalSearchParams<{ serviceId?: string }>();
  const coverHeader = useCoverHeaderScroll();
  const [token, setToken] = useState('');
  const [profile, setProfile] = useState<BookingProfile | null>(null);
  const [services, setServices] = useState<Choice[]>([]);
  const [timeSlots, setTimeSlots] = useState<Choice[]>([]);
  const [service, setService] = useState<number | ''>('');
  const [timeSlot, setTimeSlot] = useState<number | ''>('');
  const [sitio, setSitio] = useState('');
  const [purpose, setPurpose] = useState('');
  const [date, setDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const currentStep = service && sitio.trim() ? (date && timeSlot ? 3 : 2) : 1;

  useFocusEffect(useCallback(() => {
    let isActive = true;
    const loadBookingForm = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return router.replace('/login');
        const response = await api.get('appointments/', { headers: { Authorization: `Bearer ${accessToken}` } });
        if (!isActive) return;
        setToken(accessToken);
        setProfile(response.data.resident);
        setServices(response.data.services);
        setTimeSlots(response.data.time_slots);
        if (params.serviceId && response.data.services.some((item: Choice) => item.id === Number(params.serviceId))) setService(Number(params.serviceId));
      } catch (error: any) {
        Alert.alert('Unable to load booking', error?.response?.data?.message || 'Please check your connection and try again.');
      } finally {
        if (isActive) setLoading(false);
      }
    };
    setLoading(true);
    loadBookingForm();
    return () => { isActive = false; };
  }, [params.serviceId]));

  const confirmBooking = async () => {
    if (!service || !sitio.trim() || !timeSlot || !date) {
      Alert.alert('Incomplete booking', 'Select a service, enter your sitio or purok, and choose a date and time slot.');
      return;
    }
    try {
      setSubmitting(true);
      const response = await api.post('appointments/', {
        service,
        time_slot: timeSlot,
        appointment_date: formatDate(date),
        purpose,
        sitio: sitio.trim(),
      }, { headers: { Authorization: `Bearer ${token}` } });
      setPurpose(''); setSitio(''); setService(''); setTimeSlot(''); setDate(null);
      router.push({
        pathname: '/booking-success',
        params: {
          appointmentId: response.data.appointment_id,
          queueNumber: response.data.queue_number,
          service: response.data.service,
          appointmentDate: response.data.appointment_date,
          timeSlot: response.data.time_slot,
        },
      });
    } catch (error: any) {
      Alert.alert('Booking not submitted', error?.response?.data?.message || 'Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <SafeAreaView style={[s.loading, { backgroundColor: colors.background }]}><ActivityIndicator size="large" color={colors.accent} /></SafeAreaView>;

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}>
    <Animated.ScrollView style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
      <Animated.View style={[s.hero, coverHeader.headerStyle]}>
        <Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable>
        <HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} />
        <Text style={s.badge}>Online Booking</Text>
        <Text style={s.heading}>Schedule Your Appointment</Text>
        <Text style={s.subheading}>Choose your preferred service, date, and time slot.</Text>
      </Animated.View>

      <View style={[s.formCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Progress currentStep={currentStep} />
        <View style={[s.divider, { backgroundColor: colors.border }]} />
        <View style={s.sectionHeading}><View style={s.sectionIcon}><Ionicons name="person" size={14} color="#FFF" /></View><View><Text style={s.sectionTitle}>Personal Information</Text><Text style={s.sectionCopy}>Please provide accurate details.</Text></View></View>
        <View style={s.grid}>
          <ReadField label="First Name" value={profile?.first_name} />
          <ReadField label="Last Name" value={profile?.last_name} />
          <ReadField label="Middle Initial" value={profile?.middle_name ? `${profile.middle_name.charAt(0).toUpperCase()}.` : ''} />
          <ReadField label="Suffix (Extension)" value={profile?.suffix} />
          <ReadField label="Birthdate" value={profile?.birthdate} icon="calendar-outline" />
          <ReadField label="Barangay" value={profile?.barangay} />
          <ReadField label="Age" value={String(profile?.age ?? '')} />
          <ReadField label="Sex" value={profile?.sex} />
        </View>

        <View style={s.stepSection}><Text style={s.stepSectionNumber}>2</Text><Text style={s.stepSectionTitle}>Service</Text></View>
        <View style={s.twoColumns}>
          <View style={s.column}><SelectField label="Service Type" selectedValue={service} onValueChange={(value) => setService(value)} placeholder="Select a service" items={services.map((item) => ({ id: item.id, label: item.name || '' }))} compact /></View>
          <View style={s.column}><Text style={[s.label, { color: colors.text }]}>Sitio/Purok</Text><TextInput style={[s.input, s.singleLineInput, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={sitio} onChangeText={setSitio} placeholder="Enter your sitio or purok" placeholderTextColor={colors.muted} maxLength={100} /></View>
        </View>
        <Text style={[s.label, { color: colors.text }]}>Purpose</Text>
        <TextInput style={[s.input, s.purpose, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={purpose} onChangeText={setPurpose} placeholder="Briefly describe the purpose of your request." placeholderTextColor={colors.muted} multiline />
        <View style={s.stepSection}><Text style={s.stepSectionNumber}>3</Text><Text style={s.stepSectionTitle}>Date &amp; Time</Text></View>
        <View style={s.twoColumns}>
          <View style={s.column}><Text style={[s.label, { color: colors.text }]}>Date</Text><Pressable style={[s.inputShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]} onPress={() => setShowDatePicker(true)}><Text style={[date ? s.valueText : s.placeholder, { color: date ? colors.text : colors.muted }]}>{formatDate(date) || 'mm/dd/yyyy'}</Text><Ionicons name="calendar-outline" size={15} color={colors.muted} /></Pressable></View>
          <View style={s.column}><SelectField label="Select Time" selectedValue={timeSlot} onValueChange={(value) => setTimeSlot(value)} placeholder="Select time..." items={timeSlots.map((item) => ({ id: item.id, label: item.label || '' }))} compact /></View>
        </View>
        <Pressable style={[s.confirm, submitting && s.disabled]} onPress={confirmBooking} disabled={submitting}><Text style={s.confirmText}>{submitting ? 'Submitting...' : 'Confirm Booking'}</Text></Pressable>
      </View>

      <View style={[s.beforeCard, { backgroundColor: colors.surface, borderColor: colors.border }]}><View style={s.beforeTitle}><Ionicons name="information-circle" size={18} color={colors.accent} /><Text style={[s.beforeTitleText, { color: colors.accent }]}>Before You Book</Text></View><Tip icon="clipboard-outline" text="Ensure that all information provided is complete and accurate." /><Tip icon="time-outline" text="Arrive at the barangay office at least 5 minutes before your scheduled appointment." /><Tip icon="card-outline" text="Bring one (1) valid government-issued ID and any additional requirements for your selected service." /><Tip icon="checkmark-circle-outline" text="Once submitted, your appointment will be reviewed by barangay staff." /><Tip icon="close-circle-outline" text="If you are unable to attend, please cancel your appointment in advance." /></View>
    </Animated.ScrollView>
    {showDatePicker && <DateTimePicker value={date ?? new Date()} mode="date" minimumDate={new Date()} display="default" onChange={(_, selected) => { setShowDatePicker(Platform.OS === 'ios'); if (selected) setDate(selected); }} />}
  </SafeAreaView>;
}

function Progress({ currentStep }: { currentStep: number }) { const { colors } = useAppTheme(); const steps = ['Personal Information', 'Service', 'Date & Time']; return <View style={s.progress}>{steps.map((label, index) => { const step = index + 1; const complete = step < currentStep; const active = step === currentStep; return <View key={label} style={s.step}><View style={[s.stepCircle, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }, active && s.stepActive, complete && s.stepComplete]}><Text style={[s.stepNumber, { color: colors.text }, (active || complete) && s.stepNumberActive]}>{complete ? '✓' : step}</Text></View><Text style={[s.stepLabel, { color: colors.muted }, active && s.stepLabelActive, complete && s.stepLabelComplete]}>{label}</Text>{index < steps.length - 1 && <View style={[s.stepLine, { backgroundColor: colors.border }, complete && s.stepLineComplete]} />}</View>; })}</View>; }
function ReadField({ label, value = '', icon }: { label: string; value?: string; icon?: keyof typeof Ionicons.glyphMap }) { const { colors } = useAppTheme(); return <View style={s.readField}><Text style={[s.label, { color: colors.text }]}>{label}</Text><View style={[s.inputShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><Text numberOfLines={1} style={[value ? s.valueText : s.placeholder, { color: value ? colors.text : colors.muted }]}>{value || '—'}</Text>{icon && <Ionicons name={icon} size={14} color={colors.muted} />}</View></View>; }
function SelectField({ label, selectedValue, onValueChange, placeholder, items, compact = false }: { label: string; selectedValue: number | ''; onValueChange: (value: number | '') => void; placeholder: string; items: { id: number; label: string }[]; compact?: boolean }) { const { colors, isDark } = useAppTheme(); const menuText = isDark ? '#153B70' : colors.text; return <View style={!compact && s.selectBlock}><Text style={[s.label, { color: colors.text }]}>{label}</Text><View style={[s.pickerShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><Picker selectedValue={selectedValue} onValueChange={onValueChange} dropdownIconColor={colors.muted} style={[s.picker, { color: colors.text, backgroundColor: colors.surfaceAlt }, compact && s.compactPicker]} itemStyle={compact ? s.compactPickerItem : undefined}><Picker.Item label={placeholder} value="" color={isDark ? '#64748B' : '#9AA3B5'} />{items.map((item) => <Picker.Item key={item.id} label={item.label} value={item.id} color={menuText} />)}</Picker></View></View>; }
function Tip({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) { const { colors } = useAppTheme(); return <View style={[s.tip, { borderBottomColor: colors.border }]}><Ionicons name={icon} size={17} color={colors.accent} /><Text style={[s.tipText, { color: colors.muted }]}>{text}</Text></View>; }

const readableStyles = {
  badge: { backgroundColor: '#F7B844', borderRadius: 6, color: '#FFF', fontSize: 13, fontWeight: '700', overflow: 'hidden', paddingHorizontal: 11, paddingVertical: 4 },
  heading: { color: '#FFF', fontSize: 23, fontWeight: '800', marginTop: 12 },
  subheading: { color: '#FFF', fontSize: 13, marginTop: 5 },
  sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 15, height: 30, justifyContent: 'center', width: 30 },
  sectionTitle: { color: '#0646A8', fontSize: 14, fontWeight: '800' },
  sectionCopy: { color: '#7B8495', fontSize: 11, marginTop: 2 },
  label: { color: '#25314A', fontSize: 11, fontWeight: '700', marginBottom: 6 },
  inputShell: { alignItems: 'center', borderColor: '#DCE4F1', borderRadius: 7, borderWidth: 1, flexDirection: 'row', height: 44, justifyContent: 'space-between', paddingHorizontal: 10 },
  valueText: { color: '#43506A', flex: 1, fontSize: 12 },
  placeholder: { color: '#9AA3B5', flex: 1, fontSize: 12 },
  pickerShell: { borderColor: '#DCE4F1', borderRadius: 7, borderWidth: 1, height: 44, justifyContent: 'center', overflow: 'hidden' },
  picker: { color: '#43506A', fontSize: 12, height: 54, marginHorizontal: -4, marginVertical: -5 },
  compactPicker: { fontSize: 11 },
  compactPickerItem: { fontSize: 14 },
  input: { borderColor: '#DCE4F1', borderRadius: 7, borderWidth: 1, color: '#43506A', fontSize: 12, paddingHorizontal: 10 },
  singleLineInput: { height: 44 },
  purpose: { height: 64, paddingTop: 10, textAlignVertical: 'top' },
  confirmText: { color: '#FFF', fontSize: 13, fontWeight: '800' },
  beforeTitleText: { color: '#0646A8', fontSize: 14, fontWeight: '800' },
  tipText: { color: '#34415B', flex: 1, fontSize: 11, lineHeight: 16 },
  stepNumber: { color: '#31405E', fontSize: 11, fontWeight: '700' },
  stepLabel: { color: '#263650', fontSize: 9, marginTop: 5 },
} as const;

const s = StyleSheet.create({
  singleLineInput: { height: 39 },
  safe: { backgroundColor: '#07419C', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#F6F8FD', flex: 1, justifyContent: 'center' }, page: { backgroundColor: '#F6F8FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', paddingBottom: 42, paddingHorizontal: 20, paddingTop: 9 }, back: { left: 10, padding: 8, position: 'absolute', top: 6 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 20, height: 39, justifyContent: 'center', position: 'absolute', right: 16, top: 7, width: 39 }, badge: { backgroundColor: '#F7B844', borderRadius: 6, color: '#FFF', fontSize: 12, fontWeight: '700', overflow: 'hidden', paddingHorizontal: 10, paddingVertical: 3 }, heading: { color: '#FFF', fontSize: 21, fontWeight: '800', marginTop: 12 }, subheading: { color: '#FFF', fontSize: 10, marginTop: 4 }, formCard: { backgroundColor: '#FFF', borderColor: '#BDD1F6', borderRadius: 20, borderWidth: 2, marginHorizontal: 7, marginTop: -24, padding: 12 }, progress: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, step: { alignItems: 'center', flex: 1, position: 'relative' }, stepCircle: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#CAD4E8', borderRadius: 14, borderWidth: 1, height: 24, justifyContent: 'center', width: 24, zIndex: 2 }, stepActive: { backgroundColor: '#0646A8', borderColor: '#0646A8' }, stepNumber: { color: '#31405E', fontSize: 9, fontWeight: '700' }, stepNumberActive: { color: '#FFF' }, stepLabel: { color: '#263650', fontSize: 7, marginTop: 5 }, stepLabelActive: { color: '#0646A8', fontWeight: '700' }, stepLine: { backgroundColor: '#CAD4E8', height: 1, left: '64%', position: 'absolute', top: 12, width: '72%', zIndex: 1 }, divider: { backgroundColor: '#E6EBF4', height: 1, marginVertical: 7 }, sectionHeading: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 9 }, sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 12, height: 23, justifyContent: 'center', width: 23 }, sectionTitle: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, sectionCopy: { color: '#7B8495', fontSize: 7, marginTop: 1 }, grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }, readField: { marginBottom: 9, width: '24%' }, label: { color: '#25314A', fontSize: 7, fontWeight: '700', marginBottom: 5 }, inputShell: { alignItems: 'center', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, flexDirection: 'row', height: 39, justifyContent: 'space-between', paddingHorizontal: 8 }, valueText: { color: '#43506A', flex: 1, fontSize: 8 }, placeholder: { color: '#9AA3B5', flex: 1, fontSize: 8 }, selectBlock: { marginBottom: 9 }, pickerShell: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, height: 39, justifyContent: 'center', overflow: 'hidden' }, picker: { color: '#43506A', fontSize: 8, height: 52, marginHorizontal: -4, marginVertical: -7 }, compactPicker: { fontSize: 7 }, compactPickerItem: { fontSize: 12 }, input: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#43506A', fontSize: 9, paddingHorizontal: 9 }, purpose: { height: 45, paddingTop: 9, textAlignVertical: 'top' }, twoColumns: { flexDirection: 'row', gap: 8, marginTop: 9 }, column: { flex: 1 }, confirm: { alignItems: 'center', backgroundColor: '#06419C', borderRadius: 6, marginTop: 11, paddingVertical: 11 }, disabled: { opacity: 0.6 }, confirmText: { color: '#FFF', fontSize: 10, fontWeight: '800' }, beforeCard: { backgroundColor: '#FFF', borderRadius: 15, marginHorizontal: 7, marginTop: 9, padding: 12 }, beforeTitle: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 5 }, beforeTitleText: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, tip: { alignItems: 'center', borderBottomColor: '#E5EAF2', borderBottomWidth: 1, flexDirection: 'row', gap: 10, minHeight: 38, paddingVertical: 6 }, tipText: { color: '#34415B', flex: 1, fontSize: 8, lineHeight: 11 },
  stepLineComplete: { backgroundColor: '#2FB879' },
  stepComplete: { backgroundColor: '#2FB879', borderColor: '#2FB879' },
  stepLabelComplete: { color: '#209864', fontWeight: '700' },
  stepSection: { alignItems: 'center', flexDirection: 'row', gap: 7, marginTop: 12 },
  stepSectionNumber: { backgroundColor: '#0646A8', borderRadius: 12, color: '#FFF', fontSize: 9, fontWeight: '800', overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 4 },
  stepSectionTitle: { color: '#0646A8', fontSize: 12, fontWeight: '800' },
  ...(readableStyles as Record<string, object>),
  ...({
    hero: { ...residentLayout.header, alignItems: 'center', justifyContent: 'center', paddingTop: 44 },
    formCard: { ...residentLayout.overlapCard, backgroundColor: '#FFF', padding: 17 },
    beforeCard: { ...residentLayout.card, backgroundColor: '#FFF', borderWidth: 1, padding: 17 },
    sectionHeading: { alignItems: 'center', borderBottomColor: '#EEF3FA', borderBottomWidth: 1, flexDirection: 'row', gap: 12, marginBottom: 14, paddingBottom: 9 },
    grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
    readField: { marginBottom: 3, width: '48%' },
    inputShell: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, flexDirection: 'row', height: 46, justifyContent: 'space-between', paddingHorizontal: 14 },
    input: { backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, color: '#43506A', fontSize: 12, paddingHorizontal: 14 },
    pickerShell: { backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, height: 46, justifyContent: 'center', overflow: 'hidden' },
    twoColumns: { flexDirection: 'row', gap: 14, marginTop: 12 },
    stepSection: { alignItems: 'center', borderBottomColor: '#EEF3FA', borderBottomWidth: 1, flexDirection: 'row', gap: 9, marginBottom: 13, marginTop: 24, paddingBottom: 8 },
    confirm: { alignItems: 'center', backgroundColor: '#17468F', borderRadius: 10, height: 46, justifyContent: 'center', marginTop: 16 },
  } as Record<string, object>),
});
