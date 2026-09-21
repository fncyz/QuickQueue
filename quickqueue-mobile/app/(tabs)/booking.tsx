import AsyncStorage from '@react-native-async-storage/async-storage';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Picker } from '@react-native-picker/picker';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';

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
};

const formatDate = (value: Date | null) => value
  ? `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  : '';

export default function BookingScreen() {
  const [token, setToken] = useState('');
  const [profile, setProfile] = useState<BookingProfile | null>(null);
  const [services, setServices] = useState<Choice[]>([]);
  const [timeSlots, setTimeSlots] = useState<Choice[]>([]);
  const [service, setService] = useState<number | ''>('');
  const [timeSlot, setTimeSlot] = useState<number | ''>('');
  const [purpose, setPurpose] = useState('');
  const [date, setDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const loadBookingForm = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return router.replace('/login');
        setToken(accessToken);
        const response = await api.get('appointments/', { headers: { Authorization: `Bearer ${accessToken}` } });
        setProfile(response.data.resident);
        setServices(response.data.services);
        setTimeSlots(response.data.time_slots);
      } catch (error: any) {
        Alert.alert('Unable to load booking', error?.response?.data?.message || 'Please check your connection and try again.');
      } finally {
        setLoading(false);
      }
    };
    loadBookingForm();
  }, []);

  const confirmBooking = async () => {
    if (!service || !timeSlot || !date) {
      Alert.alert('Incomplete booking', 'Select a service, date, and time slot.');
      return;
    }
    try {
      setSubmitting(true);
      const response = await api.post('appointments/', {
        service,
        time_slot: timeSlot,
        appointment_date: formatDate(date),
        purpose,
      }, { headers: { Authorization: `Bearer ${token}` } });
      setPurpose(''); setService(''); setTimeSlot(''); setDate(null);
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

  if (loading) return <SafeAreaView style={s.loading}><ActivityIndicator size="large" color="#0646A8" /></SafeAreaView>;

  return <SafeAreaView style={s.safe} edges={['top']}>
    <ScrollView style={s.page} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
      <View style={s.hero}>
        <Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable>
        <Pressable onPress={() => router.push('/notifications')} style={s.avatar} accessibilityLabel="Open notifications"><Ionicons name="notifications-outline" size={22} color="#0646A8" /></Pressable>
        <Text style={s.badge}>Online Booking</Text>
        <Text style={s.heading}>Schedule Your Appointment</Text>
        <Text style={s.subheading}>Choose your preferred service, date, and time slot.</Text>
      </View>

      <View style={s.formCard}>
        <Progress />
        <View style={s.divider} />
        <View style={s.sectionHeading}><View style={s.sectionIcon}><Ionicons name="person" size={14} color="#FFF" /></View><View><Text style={s.sectionTitle}>Personal Information</Text><Text style={s.sectionCopy}>Please provide accurate details.</Text></View></View>
        <View style={s.grid}>
          <ReadField label="First Name" value={profile?.first_name} />
          <ReadField label="Last Name" value={profile?.last_name} />
          <ReadField label="Middle Initial" value={profile?.middle_name ? `${profile.middle_name.charAt(0).toUpperCase()}.` : ''} />
          <ReadField label="Suffix (Extension)" value={profile?.suffix} />
          <ReadField label="Birthdate" value={profile?.birthdate} icon="calendar-outline" />
          <ReadField label="Street Name (Purok, Sitio)" value={profile?.address} />
          <ReadField label="Age" value={String(profile?.age ?? '')} />
          <ReadField label="Sex" value={profile?.sex} />
        </View>

        <SelectField label="Service Type" selectedValue={service} onValueChange={(value) => setService(value)} placeholder="Select a service" items={services.map((item) => ({ id: item.id, label: item.name || '' }))} />
        <Text style={s.label}>Purpose</Text>
        <TextInput style={[s.input, s.purpose]} value={purpose} onChangeText={setPurpose} placeholder="Briefly describe the purpose of your request..." placeholderTextColor="#9AA3B5" multiline />
        <View style={s.twoColumns}>
          <View style={s.column}><Text style={s.label}>Date</Text><Pressable style={s.inputShell} onPress={() => setShowDatePicker(true)}><Text style={date ? s.valueText : s.placeholder}>{formatDate(date) || 'mm/dd/yyyy'}</Text><Ionicons name="calendar-outline" size={15} color="#78849B" /></Pressable></View>
          <View style={s.column}><SelectField label="Time Slot" selectedValue={timeSlot} onValueChange={(value) => setTimeSlot(value)} placeholder="Select time slot" items={timeSlots.map((item) => ({ id: item.id, label: item.label || '' }))} compact /></View>
        </View>
        <Pressable style={[s.confirm, submitting && s.disabled]} onPress={confirmBooking} disabled={submitting}><Text style={s.confirmText}>{submitting ? 'Submitting...' : 'Confirm Booking'}</Text></Pressable>
      </View>

      <View style={s.beforeCard}><View style={s.beforeTitle}><Ionicons name="information-circle" size={18} color="#0646A8" /><Text style={s.beforeTitleText}>Before You Book</Text></View><Tip icon="clipboard-outline" text="Ensure that all information provided is complete and accurate." /><Tip icon="time-outline" text="Arrive at the barangay office at least 5 minutes before your scheduled appointment." /><Tip icon="card-outline" text="Bring one (1) valid government-issued ID and any additional requirements for your selected service." /><Tip icon="checkmark-circle-outline" text="Once submitted, your appointment will be reviewed by barangay staff." /><Tip icon="close-circle-outline" text="If you are unable to attend, please cancel your appointment in advance." /></View>
    </ScrollView>
    {showDatePicker && <DateTimePicker value={date ?? new Date()} mode="date" minimumDate={new Date()} display="default" onChange={(_, selected) => { setShowDatePicker(Platform.OS === 'ios'); if (selected) setDate(selected); }} />}
  </SafeAreaView>;
}

function Progress() { const steps = ['Personal Info', 'Service', 'Date & Time', 'Review']; return <View style={s.progress}>{steps.map((label, index) => <View key={label} style={s.step}><View style={[s.stepCircle, index === 0 && s.stepActive]}><Text style={[s.stepNumber, index === 0 && s.stepNumberActive]}>{index + 1}</Text></View><Text style={[s.stepLabel, index === 0 && s.stepLabelActive]}>{label}</Text>{index < steps.length - 1 && <View style={s.stepLine} />}</View>)}</View>; }
function ReadField({ label, value = '', icon }: { label: string; value?: string; icon?: keyof typeof Ionicons.glyphMap }) { return <View style={s.readField}><Text style={s.label}>{label}</Text><View style={s.inputShell}><Text numberOfLines={1} style={value ? s.valueText : s.placeholder}>{value || '—'}</Text>{icon && <Ionicons name={icon} size={14} color="#78849B" />}</View></View>; }
function SelectField({ label, selectedValue, onValueChange, placeholder, items, compact = false }: { label: string; selectedValue: number | ''; onValueChange: (value: number | '') => void; placeholder: string; items: { id: number; label: string }[]; compact?: boolean }) { return <View style={!compact && s.selectBlock}><Text style={s.label}>{label}</Text><View style={s.pickerShell}><Picker selectedValue={selectedValue} onValueChange={onValueChange} style={s.picker}><Picker.Item label={placeholder} value="" color="#9AA3B5" />{items.map((item) => <Picker.Item key={item.id} label={item.label} value={item.id} />)}</Picker></View></View>; }
function Tip({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) { return <View style={s.tip}><Ionicons name={icon} size={17} color="#0759D9" /><Text style={s.tipText}>{text}</Text></View>; }

const s = StyleSheet.create({
  safe: { backgroundColor: '#07419C', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#F6F8FD', flex: 1, justifyContent: 'center' }, page: { backgroundColor: '#F6F8FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', paddingBottom: 42, paddingHorizontal: 20, paddingTop: 9 }, back: { left: 10, padding: 8, position: 'absolute', top: 6 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 20, height: 39, justifyContent: 'center', position: 'absolute', right: 16, top: 7, width: 39 }, badge: { backgroundColor: '#F7B844', borderRadius: 6, color: '#FFF', fontSize: 12, fontWeight: '700', overflow: 'hidden', paddingHorizontal: 10, paddingVertical: 3 }, heading: { color: '#FFF', fontSize: 21, fontWeight: '800', marginTop: 12 }, subheading: { color: '#FFF', fontSize: 10, marginTop: 4 }, formCard: { backgroundColor: '#FFF', borderColor: '#BDD1F6', borderRadius: 20, borderWidth: 2, marginHorizontal: 7, marginTop: -24, padding: 12 }, progress: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }, step: { alignItems: 'center', flex: 1, position: 'relative' }, stepCircle: { alignItems: 'center', backgroundColor: '#FFF', borderColor: '#CAD4E8', borderRadius: 14, borderWidth: 1, height: 24, justifyContent: 'center', width: 24, zIndex: 2 }, stepActive: { backgroundColor: '#0646A8', borderColor: '#0646A8' }, stepNumber: { color: '#31405E', fontSize: 9, fontWeight: '700' }, stepNumberActive: { color: '#FFF' }, stepLabel: { color: '#263650', fontSize: 7, marginTop: 5 }, stepLabelActive: { color: '#0646A8', fontWeight: '700' }, stepLine: { backgroundColor: '#CAD4E8', height: 1, left: '64%', position: 'absolute', top: 12, width: '72%', zIndex: 1 }, divider: { backgroundColor: '#E6EBF4', height: 1, marginVertical: 7 }, sectionHeading: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 9 }, sectionIcon: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 12, height: 23, justifyContent: 'center', width: 23 }, sectionTitle: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, sectionCopy: { color: '#7B8495', fontSize: 7, marginTop: 1 }, grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }, readField: { marginBottom: 9, width: '24%' }, label: { color: '#25314A', fontSize: 7, fontWeight: '700', marginBottom: 5 }, inputShell: { alignItems: 'center', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, flexDirection: 'row', height: 39, justifyContent: 'space-between', paddingHorizontal: 8 }, valueText: { color: '#43506A', flex: 1, fontSize: 8 }, placeholder: { color: '#9AA3B5', flex: 1, fontSize: 8 }, selectBlock: { marginBottom: 9 }, pickerShell: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, height: 39, justifyContent: 'center', overflow: 'hidden' }, picker: { color: '#43506A', fontSize: 8, height: 52, marginHorizontal: -4, marginVertical: -7 }, input: { borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#43506A', fontSize: 9, paddingHorizontal: 9 }, purpose: { height: 45, paddingTop: 9, textAlignVertical: 'top' }, twoColumns: { flexDirection: 'row', gap: 8, marginTop: 9 }, column: { flex: 1 }, confirm: { alignItems: 'center', backgroundColor: '#06419C', borderRadius: 6, marginTop: 11, paddingVertical: 11 }, disabled: { opacity: 0.6 }, confirmText: { color: '#FFF', fontSize: 10, fontWeight: '800' }, beforeCard: { backgroundColor: '#FFF', borderRadius: 15, marginHorizontal: 7, marginTop: 9, padding: 12 }, beforeTitle: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 5 }, beforeTitleText: { color: '#0646A8', fontSize: 10, fontWeight: '800' }, tip: { alignItems: 'center', borderBottomColor: '#E5EAF2', borderBottomWidth: 1, flexDirection: 'row', gap: 10, minHeight: 38, paddingVertical: 6 }, tipText: { color: '#34415B', flex: 1, fontSize: 8, lineHeight: 11 },
});
