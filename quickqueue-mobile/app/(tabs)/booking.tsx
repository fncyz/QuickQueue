import AsyncStorage from '@react-native-async-storage/async-storage';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Animated, Modal, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { SavedInformationBanner } from '@/components/SavedInformationBanner';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { residentLayout } from '@/constants/resident-layout';
import { useAppTheme } from '@/contexts/app-theme';
import { useConnectivity } from '@/contexts/connectivity';
import { readOfflineCache, removeOfflineCache, writeOfflineCache } from '@/services/offline-cache';
import { QuickQueueLoadingIndicator } from '@/components/QuickQueueLoadingScreen';
import { appTypography } from '@/constants/typography';

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
type BookingFormData = { resident: BookingProfile; services: Choice[]; time_slots: Choice[] };
type BookingDraft = { date: string; purpose: string; service: number | ''; sitio: string; timeSlot: number | '' };
type BookingResponse = { success: boolean; id: number; appointment_id: string; queue_number: string; service: string; appointment_date: string; time_slot: string };

const apiErrorMessage = (error: any, fallback: string) => {
  const data = error?.response?.data;
  return data?.message || data?.detail || data?.non_field_errors?.[0] || fallback;
};

const formatDate = (value: Date | null) => value
  ? `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  : '';

export default function BookingScreen() {
  const purposeRef = useRef<React.ElementRef<typeof TextInput>>(null);
  const submissionLock = useRef(false);
  const bookingCompleted = useRef(false);
  const { colors, isDark } = useAppTheme();
  const { isOnline } = useConnectivity();
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
  const [draftReady, setDraftReady] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const currentStep = service && sitio.trim() ? (date && timeSlot ? 3 : 2) : 1;

  useFocusEffect(useCallback(() => {
    let isActive = true;
    const loadBookingForm = async () => {
      const [savedForm, savedDraft] = await Promise.all([
        readOfflineCache<BookingFormData>('bookingForm'),
        readOfflineCache<BookingDraft>('bookingDraft'),
      ]);
      if (savedForm && isActive) {
        setProfile(savedForm.value.resident); setServices(savedForm.value.services); setTimeSlots(savedForm.value.time_slots);
      }
      if (savedDraft && isActive) {
        setService(savedDraft.value.service); setTimeSlot(savedDraft.value.timeSlot); setSitio(savedDraft.value.sitio); setPurpose(savedDraft.value.purpose);
        setDate(savedDraft.value.date ? new Date(`${savedDraft.value.date}T00:00:00`) : null); setHasDraft(true);
      }
      if (!isOnline) { if (isActive) { setDraftReady(true); setLoading(false); } return; }
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return router.replace('/login');
        const response = await api.get('appointments/', { headers: { Authorization: `Bearer ${accessToken}` } });
        if (!isActive) return;
        setToken(accessToken);
        setProfile(response.data.resident);
        setServices(response.data.services);
        setTimeSlots(response.data.time_slots);
        await writeOfflineCache('bookingForm', response.data as BookingFormData);
        if (savedDraft) {
          const validService = !savedDraft.value.service || response.data.services.some((item: Choice) => item.id === savedDraft.value.service);
          const validSlot = !savedDraft.value.timeSlot || response.data.time_slots.some((item: Choice) => item.id === savedDraft.value.timeSlot);
          if (!validService) setService('');
          if (!validSlot) setTimeSlot('');
          if (!validService || !validSlot) Alert.alert('Draft needs review', 'A saved service or time slot is no longer available. Please select another option.');
        }
        if (params.serviceId && response.data.services.some((item: Choice) => item.id === Number(params.serviceId))) setService(Number(params.serviceId));
      } catch (error: any) {
        if (!savedForm) Alert.alert('Unable to load booking', error?.response?.data?.message || 'Please check your connection and try again.');
      } finally {
        if (isActive) { setDraftReady(true); setLoading(false); }
      }
    };
    setLoading(true);
    loadBookingForm();
    return () => { isActive = false; };
  }, [isOnline, params.serviceId]));

  useEffect(() => {
    if (!draftReady || bookingCompleted.current) return;
    const draft: BookingDraft = { date: formatDate(date), purpose, service, sitio, timeSlot };
    const populated = Boolean(service || timeSlot || sitio.trim() || purpose.trim() || date);
    setHasDraft(populated);
    if (populated) writeOfflineCache('bookingDraft', draft);
    else removeOfflineCache('bookingDraft');
  }, [date, draftReady, purpose, service, sitio, timeSlot]);

  const deleteDraft = () => Alert.alert('Delete booking draft?', 'Your unfinished booking details will be removed from this device.', [
    { text: 'Keep Draft', style: 'cancel' },
    { text: 'Delete Draft', style: 'destructive', onPress: async () => { setPurpose(''); setSitio(''); setService(''); setTimeSlot(''); setDate(null); setHasDraft(false); await removeOfflineCache('bookingDraft'); } },
  ]);

  const saveDraft = async () => {
    const draft: BookingDraft = { date: formatDate(date), purpose, service, sitio, timeSlot };
    const populated = Boolean(service || timeSlot || sitio.trim() || purpose.trim() || date);
    if (!populated) return Alert.alert('Draft is empty', 'Enter at least one booking detail before saving a draft.');
    await writeOfflineCache('bookingDraft', draft);
    setHasDraft(true);
    Alert.alert('Saved as Draft', 'Connect to the internet to complete your booking. Your draft will not be submitted automatically.');
  };

  const confirmBooking = async () => {
    if (!service || !sitio.trim() || !timeSlot || !date) {
      Alert.alert('Incomplete booking', 'Select a service, enter your sitio or purok, and choose a date and time slot.');
      return;
    }
    if (!isOnline) {
      Alert.alert('Saved as Draft', 'Internet connection is required to finalize this booking. Your draft will remain available for review after reconnecting.');
      return;
    }
    if (submissionLock.current) return;
    submissionLock.current = true;
    try {
      setSubmitting(true);
      const accessToken = token || await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }
      const latest = await api.get<BookingFormData>('appointments/', { headers: { Authorization: `Bearer ${accessToken}` } });
      const serviceAvailable = latest.data.services.some((item) => item.id === service);
      const slotAvailable = latest.data.time_slots.some((item) => item.id === timeSlot);
      if (!serviceAvailable || !slotAvailable) {
        if (!serviceAvailable) setService('');
        if (!slotAvailable) setTimeSlot('');
        Alert.alert('Schedule no longer available', 'Please review your service and select another available time before submitting.');
        return;
      }
      const response = await api.post<BookingResponse>('appointments/', {
        service,
        time_slot: timeSlot,
        appointment_date: formatDate(date),
        purpose,
        sitio: sitio.trim(),
      }, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (response.status !== 201 || response.data.success !== true || !response.data.id || !response.data.appointment_id) {
        throw new Error('The server did not confirm the appointment creation.');
      }
      bookingCompleted.current = true;
      setHasDraft(false);
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
      removeOfflineCache('bookingDraft').catch(() => undefined);
    } catch (error: any) {
      Alert.alert('Booking not submitted', apiErrorMessage(error, error?.message || 'Please try again.'));
    } finally {
      submissionLock.current = false;
      setSubmitting(false);
    }
  };

  if (loading) return <SafeAreaView style={[s.loading, { backgroundColor: colors.background }]}><QuickQueueLoadingIndicator /></SafeAreaView>;

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}>
    <Animated.ScrollView automaticallyAdjustKeyboardInsets style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content} keyboardDismissMode="on-drag" keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
      <Animated.View style={[s.hero, coverHeader.headerStyle]}>
        <Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable>
        <HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} />
        <Text style={s.badge}>{hasDraft ? 'Draft Booking' : 'Online Booking'}</Text>
        <Text numberOfLines={2} style={s.heading}>Schedule Your Appointment</Text>
        <Text numberOfLines={2} style={s.subheading}>Choose your preferred service, date, and time slot.</Text>
      </Animated.View>

      <SavedInformationBanner />

      <View style={[s.formCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        {(!isOnline || hasDraft) && <View style={[s.draftNotice, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><Ionicons name="document-text-outline" size={18} color="#D97706" /><View style={s.draftCopy}><Text style={[s.draftTitle, { color: colors.text }]}>Draft</Text><Text style={[s.draftText, { color: colors.muted }]}>{isOnline ? 'Review your saved details before submitting.' : 'Saved on this device. Connect to finalize this booking.'}</Text></View>{hasDraft && <Pressable onPress={deleteDraft} style={s.deleteDraft}><Text style={s.deleteDraftText}>Delete</Text></Pressable>}</View>}
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
        <View style={s.fieldStack}>
          <View style={s.fullWidthField}><SelectField label="Service Type" selectedValue={service} onValueChange={(value) => setService(value)} placeholder="Select a service" items={services.map((item) => ({ id: item.id, label: item.name || '' }))} /></View>
          <View style={s.column}><Text style={[s.label, { color: colors.text }]}>Sitio/Purok</Text><TextInput style={[s.input, s.singleLineInput, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={sitio} onChangeText={setSitio} placeholder="Enter your sitio or purok" placeholderTextColor={colors.muted} maxLength={100} returnKeyType="next" onSubmitEditing={() => purposeRef.current?.focus()} /></View>
        </View>
        <Text style={[s.label, { color: colors.text }]}>Purpose</Text>
        <TextInput ref={purposeRef} style={[s.input, s.purpose, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} value={purpose} onChangeText={setPurpose} placeholder="Briefly describe the purpose of your request." placeholderTextColor={colors.muted} multiline returnKeyType="done" submitBehavior="blurAndSubmit" />
        <View style={s.stepSection}><Text style={s.stepSectionNumber}>3</Text><Text style={s.stepSectionTitle}>Date &amp; Time</Text></View>
        <View style={s.fieldStack}>
          <View style={s.column}><Text style={[s.label, { color: colors.text }]}>Date</Text><Pressable style={[s.inputShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]} onPress={() => setShowDatePicker(true)}><Text style={[date ? s.valueText : s.placeholder, { color: date ? colors.text : colors.muted }]}>{formatDate(date) || 'mm/dd/yyyy'}</Text><Ionicons name="calendar-outline" size={15} color={colors.muted} /></Pressable></View>
          <View style={s.column}><SelectField label="Select Time" selectedValue={timeSlot} onValueChange={(value) => setTimeSlot(value)} placeholder="Select time..." items={timeSlots.map((item) => ({ id: item.id, label: item.label || '' }))} /></View>
        </View>
        <Pressable style={[s.confirm, submitting && s.disabled, !isOnline && s.offlineConfirm]} onPress={isOnline ? confirmBooking : saveDraft} disabled={submitting}><Text style={s.confirmText}>{submitting ? 'Submitting...' : isOnline ? 'Confirm Booking' : 'Save as Draft'}</Text></Pressable>
      </View>

      <View style={[s.beforeCard, { backgroundColor: colors.surface, borderColor: colors.border }]}><View style={s.beforeTitle}><Ionicons name="information-circle" size={18} color={colors.accent} /><Text style={[s.beforeTitleText, { color: colors.accent }]}>Before You Book</Text></View><Tip icon="clipboard-outline" text="Ensure that all information provided is complete and accurate." /><Tip icon="time-outline" text="Arrive at the barangay office at least 5 minutes before your scheduled appointment." /><Tip icon="card-outline" text="Bring one (1) valid government-issued ID and any additional requirements for your selected service." /><Tip icon="checkmark-circle-outline" text="Once submitted, your appointment will be reviewed by barangay staff." /><Tip icon="close-circle-outline" text="If you are unable to attend, please cancel your appointment in advance." /></View>
    </Animated.ScrollView>
    {showDatePicker && <DateTimePicker value={date ?? new Date()} mode="date" minimumDate={new Date()} display="default" themeVariant={isDark ? 'dark' : 'light'} accentColor={colors.accent} onChange={(_, selected) => { setShowDatePicker(Platform.OS === 'ios'); if (selected) setDate(selected); }} />}
  </SafeAreaView>;
}

function Progress({ currentStep }: { currentStep: number }) { const { colors } = useAppTheme(); const steps = ['Personal Information', 'Service', 'Date & Time']; return <View style={s.progress}>{steps.map((label, index) => { const step = index + 1; const complete = step < currentStep; const active = step === currentStep; const isPersonalInformation = label === 'Personal Information'; return <View key={label} style={[s.step, isPersonalInformation && s.personalInformationStep]}><View style={[s.stepCircle, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }, active && s.stepActive, complete && s.stepComplete]}><Text style={[s.stepNumber, { color: colors.text }, (active || complete) && s.stepNumberActive]}>{complete ? '✓' : step}</Text></View><Text fixedFontSize={isPersonalInformation ? 11 : 11} numberOfLines={1} style={[s.stepLabel, { color: colors.muted }, active && s.stepLabelActive, complete && s.stepLabelComplete]}>{label}</Text>{index < steps.length - 1 && <View style={[s.stepLine, { backgroundColor: colors.border }, complete && s.stepLineComplete]} />}</View>; })}</View>; }
function ReadField({ label, value = '', icon }: { label: string; value?: string; icon?: keyof typeof Ionicons.glyphMap }) { const { colors } = useAppTheme(); return <View style={s.readField}><Text style={[s.label, { color: colors.text }]}>{label}</Text><View style={[s.inputShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><Text numberOfLines={1} style={[value ? s.valueText : s.placeholder, { color: value ? colors.text : colors.muted }]}>{value || '—'}</Text>{icon && <Ionicons name={icon} size={14} color={colors.muted} />}</View></View>; }
function SelectField({ label, selectedValue, onValueChange, placeholder, items }: { label: string; selectedValue: number | ''; onValueChange: (value: number | '') => void; placeholder: string; items: { id: number; label: string }[] }) {
  const { colors } = useAppTheme();
  const [open, setOpen] = useState(false);
  const selectedLabel = items.find((item) => item.id === selectedValue)?.label;
  return <View style={s.selectBlock}>
    <Text style={[s.label, appTypography.fieldLabel, { color: colors.text }]}>{label}</Text>
    <Pressable accessibilityRole="button" accessibilityLabel={`${label}: ${selectedLabel || placeholder}`} onPress={() => setOpen(true)} style={[s.pickerShell, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}>
      <Text ellipsizeMode="tail" numberOfLines={1} style={[s.pickerValue, { color: selectedLabel ? colors.text : colors.muted }]}>{selectedLabel || placeholder}</Text>
      <Ionicons name="chevron-down" size={18} color={colors.muted} />
    </Pressable>
    <Modal animationType="fade" onRequestClose={() => setOpen(false)} transparent visible={open}>
      <Pressable onPress={() => setOpen(false)} style={s.pickerBackdrop}>
        <Pressable onPress={(event) => event.stopPropagation()} style={[s.pickerMenu, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <View style={[s.pickerHeader, { borderBottomColor: colors.border }]}><Text style={[s.pickerTitle, { color: colors.text }]}>{label}</Text><Pressable accessibilityLabel="Close selector" onPress={() => setOpen(false)} style={s.pickerClose}><Ionicons name="close" size={22} color={colors.muted} /></Pressable></View>
          <ScrollView contentContainerStyle={s.pickerOptions} showsVerticalScrollIndicator={false}>{items.map((item) => <Pressable key={item.id} onPress={() => { onValueChange(item.id); setOpen(false); }} style={[s.pickerOption, { borderBottomColor: colors.border }, selectedValue === item.id && { backgroundColor: colors.iconBackground }]}><Text numberOfLines={2} style={[s.pickerOptionText, { color: colors.text }]}>{item.label}</Text>{selectedValue === item.id && <Ionicons name="checkmark-circle" size={20} color={colors.accent} />}</Pressable>)}</ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  </View>;
}
function Tip({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) { const { colors } = useAppTheme(); return <View style={[s.tip, { borderBottomColor: colors.border }]}><Ionicons name={icon} size={17} color={colors.accent} /><Text style={[s.tipText, { color: colors.muted }]}>{text}</Text></View>; }

const readableStyles = {
  badge: { backgroundColor: '#F7B844', borderRadius: 6, color: '#FFF', fontSize: 13, fontWeight: '700', overflow: 'hidden', paddingHorizontal: 11, paddingVertical: 4 },
  heading: { ...appTypography.pageTitle, color: '#FFF', marginTop: 9, maxWidth: '76%', textAlign: 'center' },
  subheading: { ...appTypography.pageSubtitle, color: '#FFF', marginTop: 5, maxWidth: '88%', textAlign: 'center' },
  sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 15, height: 30, justifyContent: 'center', width: 30 },
  sectionTitle: { ...appTypography.sectionTitle, color: '#0646A8' },
  sectionCopy: { color: '#7B8495', fontSize: 11, marginTop: 2 },
  label: { ...appTypography.fieldLabel, color: '#25314A', marginBottom: 6 },
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
  stepLabel: { color: '#263650', fontSize: 7, marginTop: 5, textAlign: 'center', width: '100%' },
} as const;

const s = StyleSheet.create({
  singleLineInput: { height: 39 },
  safe: { backgroundColor: '#07419C', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#F6F8FD', flex: 1, justifyContent: 'center' }, page: { backgroundColor: '#F6F8FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', paddingBottom: 42, paddingHorizontal: 20, paddingTop: 9 }, back: { left: 10, padding: 8, position: 'absolute', top: 6 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 20, height: 39, justifyContent: 'center', position: 'absolute', right: 16, top: 7, width: 39 }, badge: { backgroundColor: '#F7B844', borderRadius: 6, color: '#FFF', fontSize: 12, fontWeight: '700', overflow: 'hidden', paddingHorizontal: 10, paddingVertical: 3 }, heading: { color: '#FFF', fontSize: 21, fontWeight: '800', marginTop: 12 }, subheading: { color: '#FFF', fontSize: 10, marginTop: 4 }, formCard: { backgroundColor: '#FFF', borderColor: '#BDD1F6', borderRadius: 20, borderWidth: 2, marginHorizontal: 7, marginTop: -24, padding: 12 }, progress: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, step: { alignItems: 'center', flex: 1, position: 'relative' }, stepCircle: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#CAD4E8', borderRadius: 14, borderWidth: 1, height: 24, justifyContent: 'center', width: 24, zIndex: 2 }, stepActive: { backgroundColor: '#0646A8', borderColor: '#0646A8' }, stepNumber: { color: '#31405E', fontSize: 9, fontWeight: '700' }, stepNumberActive: { color: '#FFF' }, stepLabel: { color: '#263650', fontSize: 7, marginTop: 5 }, stepLabelActive: { color: '#0646A8', fontWeight: '700' }, stepLine: { backgroundColor: '#CAD4E8', height: 1, left: '64%', position: 'absolute', top: 12, width: '72%', zIndex: 1 }, divider: { backgroundColor: '#E6EBF4', height: 1, marginVertical: 7 }, sectionHeading: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 9 }, sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 12, height: 23, justifyContent: 'center', width: 23 }, sectionTitle: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, sectionCopy: { color: '#7B8495', fontSize: 7, marginTop: 1 }, grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }, readField: { marginBottom: 9, width: '24%' }, label: { color: '#25314A', fontSize: 7, fontWeight: '700', marginBottom: 5 }, inputShell: { alignItems: 'center', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, flexDirection: 'row', height: 39, justifyContent: 'space-between', paddingHorizontal: 8 }, valueText: { color: '#43506A', flex: 1, fontSize: 8 }, placeholder: { color: '#9AA3B5', flex: 1, fontSize: 8 }, selectBlock: { marginBottom: 9 }, pickerShell: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, height: 39, justifyContent: 'center', overflow: 'hidden' }, picker: { color: '#43506A', fontSize: 8, height: 52, marginHorizontal: -4, marginVertical: -7 }, compactPicker: { fontSize: 7 }, compactPickerItem: { fontSize: 12 }, input: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#43506A', fontSize: 9, paddingHorizontal: 9 }, purpose: { height: 45, paddingTop: 9, textAlignVertical: 'top' }, twoColumns: { flexDirection: 'row', gap: 8, marginTop: 9 }, column: { flex: 1 }, confirm: { alignItems: 'center', backgroundColor: '#06419C', borderRadius: 6, marginTop: 11, paddingVertical: 11 }, disabled: { opacity: 0.6 }, confirmText: { color: '#FFF', fontSize: 10, fontWeight: '800' }, beforeCard: { backgroundColor: '#FFF', borderRadius: 15, marginHorizontal: 7, marginTop: 9, padding: 12 }, beforeTitle: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 5 }, beforeTitleText: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, tip: { alignItems: 'center', borderBottomColor: '#E5EAF2', borderBottomWidth: 1, flexDirection: 'row', gap: 10, minHeight: 38, paddingVertical: 6 }, tipText: { color: '#34415B', flex: 1, fontSize: 8, lineHeight: 11 },
  stepLineComplete: { backgroundColor: '#2FB879' },
  personalInformationStep: { flex: 1.35 },
  fieldStack: { gap: 14, marginTop: 12, width: '100%' },
  fullWidthField: { width: '100%' },
  pickerItem: { fontSize: 14 },
  pickerValue: { ...appTypography.input, flex: 1, flexShrink: 1, minWidth: 0, paddingRight: 12 },
  pickerBackdrop: { alignItems: 'center', backgroundColor: 'rgba(1, 8, 18, 0.72)', flex: 1, justifyContent: 'center', padding: 18 },
  pickerMenu: { borderRadius: 18, borderWidth: 1, maxHeight: '70%', maxWidth: 520, overflow: 'hidden', width: '100%' },
  pickerHeader: { alignItems: 'center', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 58, paddingLeft: 18, paddingRight: 8 },
  pickerTitle: { ...appTypography.sectionTitle, flex: 1 },
  pickerClose: { alignItems: 'center', height: 44, justifyContent: 'center', width: 44 },
  pickerOptions: { paddingBottom: 8 },
  pickerOption: { alignItems: 'center', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 52, paddingHorizontal: 18, paddingVertical: 10 },
  pickerOptionText: { ...appTypography.body, flex: 1, flexShrink: 1, minWidth: 0, paddingRight: 12 },
  draftNotice: { alignItems: 'center', borderRadius: 12, borderWidth: 1, flexDirection: 'row', gap: 9, marginBottom: 14, padding: 10 },
  draftCopy: { flex: 1 },
  draftTitle: { fontSize: 11, fontWeight: '800' },
  draftText: { fontSize: 9, lineHeight: 13, marginTop: 2 },
  deleteDraft: { borderColor: '#E65B65', borderRadius: 8, borderWidth: 1, paddingHorizontal: 9, paddingVertical: 6 },
  deleteDraftText: { color: '#D93B47', fontSize: 9, fontWeight: '800' },
  offlineConfirm: { backgroundColor: '#D97706' },
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
    grid: { gap: 12, width: '100%' },
    readField: { width: '100%' },
    inputShell: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, flexDirection: 'row', height: 46, justifyContent: 'space-between', paddingHorizontal: 14 },
    input: { backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, color: '#43506A', fontSize: 12, paddingHorizontal: 14 },
    pickerShell: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#E8EEF6', borderRadius: 16, borderWidth: 1, flexDirection: 'row', height: 46, justifyContent: 'space-between', overflow: 'hidden', paddingHorizontal: 14 },
    fieldStack: { gap: 14, marginTop: 12, width: '100%' },
    fullWidthField: { width: '100%' },
    column: { width: '100%' },
    pickerItem: { fontSize: 14 },
    stepSection: { alignItems: 'center', borderBottomColor: '#EEF3FA', borderBottomWidth: 1, flexDirection: 'row', gap: 9, marginBottom: 13, marginTop: 24, paddingBottom: 8 },
    confirm: { alignItems: 'center', backgroundColor: '#17468F', borderRadius: 10, flexDirection: 'row', gap: 8, height: 46, justifyContent: 'center', marginTop: 16 },
  } as Record<string, object>),
});
