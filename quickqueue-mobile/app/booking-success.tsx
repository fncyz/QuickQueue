import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function BookingSuccessScreen() {
  const params = useLocalSearchParams<{ appointmentId: string; queueNumber: string; service: string; appointmentDate: string; timeSlot: string }>();

  return <SafeAreaView style={s.safe} edges={['top', 'bottom']}>
    <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
      <View style={s.successArea}>
        <View style={s.sparkOne} /><View style={s.sparkTwo} /><View style={s.sparkThree} />
        <View style={s.successHalo}><View style={s.successSeal}><Ionicons name="checkmark" size={45} color="#FFFFFF" /></View></View>
        <Text style={s.heading}>Appointment Submitted!</Text>
        <Text style={s.subheading}>Your appointment has been submitted successfully.</Text>
      </View>

      <View style={s.referenceCard}>
        <View style={s.referenceIcon}><Ionicons name="document-text-outline" size={25} color="#0875FF" /></View>
        <View style={s.referenceCopy}><Text style={s.referenceLabel}>Appointment ID</Text><Text style={s.referenceNumber}>{params.appointmentId}</Text><Text style={s.queueNumber}>Queue number: {params.queueNumber}</Text></View>
        <View style={s.submitted}><View style={s.submittedDot} /><Text style={s.submittedText}>Submitted</Text></View>
      </View>

      <View style={s.details}><Detail icon="briefcase-outline" label="Service" value={params.service} /><Detail icon="calendar-outline" label="Appointment Date" value={params.appointmentDate} /><Detail icon="time-outline" label="Time Slot" value={params.timeSlot} /></View>

      <View style={s.progressHeader}><Text style={s.progressTitle}>Appointment Progress</Text><View style={s.current}><Text style={s.currentLabel}>Current Status</Text><Text style={s.currentValue}>Under Review</Text></View></View>
      <View style={s.progressCard}>
        <ProgressItem icon="checkmark" title="Submitted" detail="Your appointment has been received successfully." active color="#3FD58C" />
        <View style={s.progressLine} />
        <ProgressItem icon="time-outline" title="Under Review" detail="Your appointment is currently being reviewed by barangay staff." active color="#3887F6" badge="In Progress" />
        <View style={[s.progressLine, s.progressLinePending]} />
        <ProgressItem icon="checkmark" title="Approved" detail="You will be notified once your appointment is approved." color="#B9C8DE" badge="Pending" />
      </View>

      <Pressable onPress={() => router.replace('/queue')} style={s.primary}><Text style={s.primaryText}>Track Status</Text><Ionicons name="chevron-forward" size={19} color="#FFFFFF" /></Pressable>
      <Pressable onPress={() => router.replace('/(tabs)')} style={s.secondary}><Text style={s.secondaryText}>Back to Home</Text></Pressable>
    </ScrollView>
  </SafeAreaView>;
}

function Detail({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value?: string }) {
  return <View style={s.detail}><Ionicons name={icon} size={17} color="#1978EC" /><View><Text style={s.detailLabel}>{label}</Text><Text style={s.detailValue}>{value || '—'}</Text></View></View>;
}

function ProgressItem({ icon, title, detail, active = false, color, badge }: { icon: keyof typeof Ionicons.glyphMap; title: string; detail: string; active?: boolean; color: string; badge?: string }) {
  return <View style={s.progressItem}><View style={[s.progressIcon, { backgroundColor: active ? color : '#FFFFFF', borderColor: color }]}><Ionicons name={icon} size={18} color={active ? '#FFFFFF' : color} /></View><View style={s.progressCopy}><Text style={[s.progressItemTitle, !active && s.pendingText]}>{title}</Text><Text style={[s.progressDetail, !active && s.pendingText]}>{detail}</Text></View>{badge && <Text style={[s.progressBadge, !active && s.pendingBadge]}>{badge}</Text>}</View>;
}

const s = StyleSheet.create({
  safe: { backgroundColor: '#FFFFFF', flex: 1 }, content: { padding: 18, paddingBottom: 28 }, successArea: { alignItems: 'center', paddingBottom: 17, paddingTop: 25, position: 'relative' }, successHalo: { alignItems: 'center', backgroundColor: '#E8FBF4', borderRadius: 50, height: 100, justifyContent: 'center', width: 100 }, successSeal: { alignItems: 'center', backgroundColor: '#39CC91', borderRadius: 34, height: 68, justifyContent: 'center', shadowColor: '#28B77F', shadowOffset: { width: 0, height: 5 }, shadowOpacity: 0.25, shadowRadius: 8, elevation: 5, width: 68 }, sparkOne: { backgroundColor: '#42D19A', borderRadius: 3, height: 6, left: '31%', position: 'absolute', top: 30, width: 6 }, sparkTwo: { backgroundColor: '#36A4F5', borderRadius: 3, height: 6, position: 'absolute', right: '27%', top: 73, width: 6 }, sparkThree: { backgroundColor: '#42D19A', height: 4, left: '28%', position: 'absolute', top: 90, transform: [{ rotate: '-45deg' }], width: 13 }, heading: { color: '#082E78', fontSize: 21, fontWeight: '800', marginTop: 17 }, subheading: { color: '#7189C3', fontSize: 12, lineHeight: 17, marginTop: 7, maxWidth: 260, textAlign: 'center' }, referenceCard: { alignItems: 'center', backgroundColor: '#F3F8FF', borderColor: '#DDE9F9', borderRadius: 13, borderWidth: 1, flexDirection: 'row', marginTop: 2, padding: 14 }, referenceIcon: { alignItems: 'center', backgroundColor: '#E1EEFF', borderRadius: 22, height: 44, justifyContent: 'center', width: 44 }, referenceCopy: { flex: 1, marginLeft: 12 }, referenceLabel: { color: '#6A7FAF', fontSize: 9, fontWeight: '600', textTransform: 'uppercase' }, referenceNumber: { color: '#092F7C', fontSize: 16, fontWeight: '900', letterSpacing: 0.3, marginTop: 3 }, queueNumber: { color: '#6A7FAF', fontSize: 8, marginTop: 3 }, submitted: { alignItems: 'center', backgroundColor: '#DDF7ED', borderRadius: 12, flexDirection: 'row', gap: 4, paddingHorizontal: 9, paddingVertical: 5 }, submittedDot: { backgroundColor: '#27C986', borderRadius: 3, height: 6, width: 6 }, submittedText: { color: '#17A66E', fontSize: 8, fontWeight: '800' }, details: { borderColor: '#E4EBF5', borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', marginTop: 12, padding: 11 }, detail: { alignItems: 'center', flex: 1, gap: 6 }, detailLabel: { color: '#7B8CA9', fontSize: 7, textAlign: 'center' }, detailValue: { color: '#17366C', fontSize: 8, fontWeight: '700', marginTop: 2, textAlign: 'center' }, progressHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 21 }, progressTitle: { color: '#092F75', fontSize: 14, fontWeight: '800' }, current: { alignItems: 'center', flexDirection: 'row', gap: 8 }, currentLabel: { color: '#7A8CAC', fontSize: 8 }, currentValue: { backgroundColor: '#E8F2FF', borderRadius: 10, color: '#1978EC', fontSize: 8, overflow: 'hidden', paddingHorizontal: 9, paddingVertical: 5 }, progressCard: { borderColor: '#E1E9F4', borderRadius: 13, borderWidth: 1, marginTop: 10, padding: 15 }, progressItem: { alignItems: 'center', flexDirection: 'row', minHeight: 61 }, progressIcon: { alignItems: 'center', borderRadius: 16, borderWidth: 2, height: 32, justifyContent: 'center', width: 32 }, progressCopy: { flex: 1, marginLeft: 14 }, progressItemTitle: { color: '#153877', fontSize: 11, fontWeight: '800' }, progressDetail: { color: '#7186B1', fontSize: 8, lineHeight: 12, marginTop: 4 }, pendingText: { color: '#9EADCA' }, progressBadge: { backgroundColor: '#E7F2FF', borderRadius: 9, color: '#1878EB', fontSize: 7, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 5 }, pendingBadge: { backgroundColor: 'transparent', color: '#A7B5D0' }, progressLine: { backgroundColor: '#45D394', height: 23, marginLeft: 15, width: 2 }, progressLinePending: { backgroundColor: '#CBD7E9' }, primary: { alignItems: 'center', backgroundColor: '#439BF4', borderRadius: 24, flexDirection: 'row', justifyContent: 'center', marginTop: 17, minHeight: 49, paddingHorizontal: 18 }, primaryText: { color: '#FFFFFF', flex: 1, fontSize: 13, fontWeight: '800', textAlign: 'center' }, secondary: { alignItems: 'center', borderColor: '#5D9DFF', borderRadius: 24, borderWidth: 1, justifyContent: 'center', marginTop: 11, minHeight: 47 }, secondaryText: { color: '#126BDE', fontSize: 12, fontWeight: '800' },
});
