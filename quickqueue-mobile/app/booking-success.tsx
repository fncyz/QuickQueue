import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAppTheme } from '@/contexts/app-theme';
import { SuccessAnimation } from '@/components/SuccessAnimation';
import { SpecialServicesIcon } from '@/components/SpecialServicesIcon';

export default function BookingSuccessScreen() {
  const { colors, isDark } = useAppTheme();
  const params = useLocalSearchParams<{ appointmentId: string; queueNumber: string; service: string; appointmentDate: string; timeSlot: string; status?: string; statusCode?: string; isEvent?: string; eventBookingId?: string; bookingReference?: string }>();
  const currentStatus = params.statusCode === 'P' ? 'Under Review' : (params.status || 'Under Review');
  const approved = ['C', 'O', 'D'].includes(params.statusCode || '');

  if (params.isEvent === 'true' && params.eventBookingId) return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top', 'bottom']}><ScrollView contentContainerStyle={s.content}><View style={s.successArea}><SuccessAnimation /><Text style={[s.heading, isDark && s.darkHeading]}>Special Service Booked!</Text><Text style={[s.subheading, isDark && s.darkSecondary]}>Your secure QR booking pass is ready.</Text></View><View style={[s.referenceCard, isDark && s.darkCard]}><View style={[s.referenceIcon, isDark && s.darkBlueTint]}><Ionicons name="qr-code-outline" size={27} color={isDark ? '#79AEEF' : '#0875FF'} /></View><View style={s.referenceCopy}><Text style={[s.referenceLabel, isDark && s.darkSecondary]}>Booking Reference</Text><Text style={[s.referenceNumber, isDark && s.darkPrimaryText]}>{params.bookingReference}</Text><Text style={[s.queueNumber, isDark && s.darkSecondary]}>Present your QR pass at the event venue.</Text></View><View style={[s.submitted, isDark && s.darkGreenTint]}><Text style={[s.submittedText, isDark && s.darkGreenText]}>Confirmed</Text></View></View><View style={[s.details, isDark && s.darkCard]}><SpecialServiceDetail label="Special Service" value={params.service} /><Detail icon="calendar-outline" label="Event Date" value={params.appointmentDate} /></View><Pressable onPress={() => router.replace({ pathname: '/event-pass' as never, params: { bookingId: params.eventBookingId } })} style={[s.primary, isDark && s.darkPrimaryButton]}><Text style={[s.primaryText, isDark && s.darkPrimaryText]}>View QR Pass</Text><Ionicons name="qr-code-outline" size={20} color="#FFF" /></Pressable><Pressable onPress={() => router.replace('/(tabs)')} style={[s.secondary, isDark && s.darkSecondaryButton]}><Text style={[s.secondaryText, isDark && s.darkSectionHeading]}>Back to Home</Text></Pressable></ScrollView></SafeAreaView>;

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
    <ScrollView style={{ backgroundColor: colors.background }} contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
      <View style={s.successArea}>
        <View style={s.sparkOne} /><View style={s.sparkTwo} /><View style={s.sparkThree} />
        <SuccessAnimation />
        <Text style={[s.heading, isDark && s.darkHeading]}>Appointment Submitted!</Text>
        <Text style={[s.subheading, isDark && s.darkSecondary]}>Your booking was saved successfully.</Text>
      </View>

      <View style={[s.referenceCard, isDark && s.darkCard]}>
        <View style={[s.referenceIcon, isDark && s.darkBlueTint]}><Ionicons name="document-text-outline" size={25} color={isDark ? '#79AEEF' : '#0875FF'} /></View>
        <View style={s.referenceCopy}><Text style={[s.referenceLabel, isDark && s.darkSecondary]}>Appointment ID</Text><Text style={[s.referenceNumber, isDark && s.darkPrimaryText]}>{params.appointmentId}</Text><Text style={[s.queueNumber, isDark && s.darkSecondary]}>Queue number: {params.queueNumber}</Text></View>
        <View style={[s.submitted, isDark && s.darkGreenTint]}><View style={[s.submittedDot, isDark && s.darkGreen]} /><Text style={[s.submittedText, isDark && s.darkGreenText]}>Submitted</Text></View>
      </View>

      <View style={[s.details, isDark && s.darkCard]}><Detail icon="briefcase-outline" label="Service" value={params.service} /><Detail icon="calendar-outline" label="Appointment Date" value={params.appointmentDate} /><Detail icon="time-outline" label="Time Slot" value={params.timeSlot} /></View>

      <View style={s.progressHeader}><Text style={[s.progressTitle, isDark && s.darkSectionHeading]}>Appointment Progress</Text><View style={s.current}><Text style={[s.currentLabel, isDark && s.darkSecondary]}>Current Status</Text><Text style={[s.currentValue, isDark && s.darkBluePill]}>{currentStatus}</Text></View></View>
      <View style={[s.progressCard, isDark && s.darkCard]}>
        <ProgressItem icon="checkmark" title="Submitted" detail="Your appointment has been received successfully." active color={isDark ? '#65BE91' : '#3FD58C'} />
        <View style={[s.progressLine, isDark && s.darkGreenLine]} />
        <ProgressItem icon="time-outline" title="Under Review" detail="Your appointment is currently being reviewed by barangay staff." active color={isDark ? '#6D9FDC' : '#3887F6'} badge="In Progress" />
        <View style={[s.progressLine, !approved && s.progressLinePending, isDark && (approved ? s.darkGreenLine : s.darkPendingLine)]} />
        <ProgressItem icon="checkmark" title="Approved" detail={approved ? 'Your appointment has been approved.' : 'You will be notified once your appointment is approved.'} active={approved} color={approved ? (isDark ? '#65BE91' : '#3FD58C') : (isDark ? '#63738A' : '#B9C8DE')} badge={approved ? 'Approved' : 'Pending'} />
      </View>

      <Pressable onPress={() => router.replace('/queue')} style={[s.primary, isDark && s.darkPrimaryButton]}><Text style={[s.primaryText, isDark && s.darkPrimaryText]}>Track Status</Text><Ionicons name="chevron-forward" size={19} color={isDark ? '#E8EDF5' : '#FFFFFF'} /></Pressable>
      <Pressable onPress={() => router.replace('/(tabs)')} style={[s.secondary, isDark && s.darkSecondaryButton]}><Text style={[s.secondaryText, isDark && s.darkSectionHeading]}>Back to Home</Text></Pressable>
    </ScrollView>
  </SafeAreaView>;
}

function Detail({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value?: string }) {
  const { isDark } = useAppTheme();
  return <View style={s.detail}><Ionicons name={icon} size={17} color={isDark ? '#79AEEF' : '#1978EC'} /><View><Text style={[s.detailLabel, isDark && s.darkSecondary]}>{label}</Text><Text style={[s.detailValue, isDark && s.darkPrimaryText]}>{value || '—'}</Text></View></View>;
}

function SpecialServiceDetail({ label, value }: { label: string; value?: string }) {
  const { isDark } = useAppTheme();
  return <View style={s.detail}><SpecialServicesIcon size={24} /><View><Text style={[s.detailLabel, isDark && s.darkSecondary]}>{label}</Text><Text style={[s.detailValue, isDark && s.darkPrimaryText]}>{value || '—'}</Text></View></View>;
}

function ProgressItem({ icon, title, detail, active = false, color, badge }: { icon: keyof typeof Ionicons.glyphMap; title: string; detail: string; active?: boolean; color: string; badge?: string }) {
  const { isDark } = useAppTheme();
  return <View style={s.progressItem}><View style={[s.progressIcon, { backgroundColor: active ? color : isDark ? '#1B293C' : '#FFFFFF', borderColor: color }]}><Ionicons name={icon} size={18} color={active ? (isDark ? '#E8EDF5' : '#FFFFFF') : color} /></View><View style={s.progressCopy}><Text style={[s.progressItemTitle, !active && s.pendingText, isDark && (active ? s.darkPrimaryText : s.darkPendingText)]}>{title}</Text><Text style={[s.progressDetail, !active && s.pendingText, isDark && (active ? s.darkSecondary : s.darkPendingText)]}>{detail}</Text></View>{badge && <Text style={[s.progressBadge, isDark && s.darkBluePill, !active && s.pendingBadge, isDark && !active && s.darkPendingPill]}>{badge}</Text>}</View>;
}

const s = StyleSheet.create({
  safe: { backgroundColor: '#FFFFFF', flex: 1 }, content: { padding: 18, paddingBottom: 28 }, successArea: { alignItems: 'center', paddingBottom: 17, paddingTop: 25, position: 'relative' }, successHalo: { alignItems: 'center', backgroundColor: '#E8FBF4', borderRadius: 50, height: 100, justifyContent: 'center', width: 100 }, successSeal: { alignItems: 'center', backgroundColor: '#39CC91', borderRadius: 34, height: 68, justifyContent: 'center', shadowColor: '#28B77F', shadowOffset: { width: 0, height: 5 }, shadowOpacity: 0.25, shadowRadius: 8, elevation: 5, width: 68 }, sparkOne: { backgroundColor: '#42D19A', borderRadius: 3, height: 6, left: '31%', position: 'absolute', top: 30, width: 6 }, sparkTwo: { backgroundColor: '#36A4F5', borderRadius: 3, height: 6, position: 'absolute', right: '27%', top: 73, width: 6 }, sparkThree: { backgroundColor: '#42D19A', height: 4, left: '28%', position: 'absolute', top: 90, transform: [{ rotate: '-45deg' }], width: 13 }, heading: { color: '#082E78', fontSize: 21, fontWeight: '800', marginTop: 17 }, subheading: { color: '#7189C3', fontSize: 12, lineHeight: 17, marginTop: 7, maxWidth: 260, textAlign: 'center' }, referenceCard: { alignItems: 'center', backgroundColor: '#F3F8FF', borderColor: '#DDE9F9', borderRadius: 13, borderWidth: 1, flexDirection: 'row', marginTop: 2, padding: 14 }, referenceIcon: { alignItems: 'center', backgroundColor: '#E1EEFF', borderRadius: 22, height: 44, justifyContent: 'center', width: 44 }, referenceCopy: { flex: 1, marginLeft: 12 }, referenceLabel: { color: '#6A7FAF', fontSize: 9, fontWeight: '600', textTransform: 'uppercase' }, referenceNumber: { color: '#092F7C', fontSize: 16, fontWeight: '900', letterSpacing: 0.3, marginTop: 3 }, queueNumber: { color: '#6A7FAF', fontSize: 8, marginTop: 3 }, submitted: { alignItems: 'center', backgroundColor: '#DDF7ED', borderRadius: 12, flexDirection: 'row', gap: 4, paddingHorizontal: 9, paddingVertical: 5 }, submittedDot: { backgroundColor: '#27C986', borderRadius: 3, height: 6, width: 6 }, submittedText: { color: '#17A66E', fontSize: 8, fontWeight: '800' }, details: { borderColor: '#E4EBF5', borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', marginTop: 12, padding: 11 }, detail: { alignItems: 'center', flex: 1, gap: 6 }, detailLabel: { color: '#7B8CA9', fontSize: 7, textAlign: 'center' }, detailValue: { color: '#17366C', fontSize: 8, fontWeight: '700', marginTop: 2, textAlign: 'center' }, progressHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 21 }, progressTitle: { color: '#092F75', fontSize: 14, fontWeight: '800' }, current: { alignItems: 'center', flexDirection: 'row', gap: 8 }, currentLabel: { color: '#7A8CAC', fontSize: 8 }, currentValue: { backgroundColor: '#E8F2FF', borderRadius: 10, color: '#1978EC', fontSize: 8, overflow: 'hidden', paddingHorizontal: 9, paddingVertical: 5 }, progressCard: { borderColor: '#E1E9F4', borderRadius: 13, borderWidth: 1, marginTop: 10, padding: 15 }, progressItem: { alignItems: 'center', flexDirection: 'row', minHeight: 61 }, progressIcon: { alignItems: 'center', borderRadius: 16, borderWidth: 2, height: 32, justifyContent: 'center', width: 32 }, progressCopy: { flex: 1, marginLeft: 14 }, progressItemTitle: { color: '#153877', fontSize: 11, fontWeight: '800' }, progressDetail: { color: '#7186B1', fontSize: 8, lineHeight: 12, marginTop: 4 }, pendingText: { color: '#9EADCA' }, progressBadge: { backgroundColor: '#E7F2FF', borderRadius: 9, color: '#1878EB', fontSize: 7, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 5 }, pendingBadge: { backgroundColor: 'transparent', color: '#A7B5D0' }, progressLine: { backgroundColor: '#45D394', height: 23, marginLeft: 15, width: 2 }, progressLinePending: { backgroundColor: '#CBD7E9' }, primary: { alignItems: 'center', backgroundColor: '#439BF4', borderRadius: 24, flexDirection: 'row', justifyContent: 'center', marginTop: 17, minHeight: 49, paddingHorizontal: 18 }, primaryText: { color: '#FFFFFF', flex: 1, fontSize: 13, fontWeight: '800', textAlign: 'center' }, secondary: { alignItems: 'center', borderColor: '#5D9DFF', borderRadius: 24, borderWidth: 1, justifyContent: 'center', marginTop: 11, minHeight: 47 }, secondaryText: { color: '#126BDE', fontSize: 12, fontWeight: '800' },
  darkCard: { backgroundColor: '#131E30', borderColor: '#26364D', shadowColor: '#050A12', shadowOffset: { height: 2, width: 0 }, shadowOpacity: 0.24, shadowRadius: 7, elevation: 2 }, darkHeading: { color: '#E8EDF5' }, darkPrimaryText: { color: '#E8EDF5' }, darkSecondary: { color: '#9DACC0' }, darkSectionHeading: { color: '#86B5EE' }, darkBlueTint: { backgroundColor: '#1B304C' }, darkBluePill: { backgroundColor: '#1B304C', color: '#8AB8EE' }, darkGreenTint: { backgroundColor: '#19362C' }, darkGreen: { backgroundColor: '#65BE91' }, darkGreenText: { color: '#83CDA6' }, darkGreenLine: { backgroundColor: '#65BE91' }, darkPendingLine: { backgroundColor: '#45546A' }, darkPendingText: { color: '#738198' }, darkPendingPill: { backgroundColor: '#202C3D', color: '#8290A5' }, darkPrimaryButton: { backgroundColor: '#326FAE' }, darkSecondaryButton: { borderColor: '#547EAF' },
});
