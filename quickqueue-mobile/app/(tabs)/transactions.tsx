import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';

type Transaction = { id: number; appointment_id: string; service: string; status: string; status_code: string; date_booked: string; appointment_date: string; date_claimed: string | null; time_slot: string; barangay: string; queue_number: string };
type Filter = 'All' | 'Pending' | 'Completed' | 'Cancelled' | 'Expired';
const filters: { label: Filter; icon?: keyof typeof Ionicons.glyphMap }[] = [{ label: 'All' }, { label: 'Pending', icon: 'time-outline' }, { label: 'Completed', icon: 'checkmark-circle-outline' }, { label: 'Cancelled', icon: 'close-circle-outline' }, { label: 'Expired', icon: 'alert-circle-outline' }];

export default function TransactionsScreen() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filter, setFilter] = useState<Filter>('All');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    try {
      const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) return router.replace('/login');
      setToken(accessToken);
      const response = await api.get('transactions/', { headers: { Authorization: `Bearer ${accessToken}` } });
      setTransactions(response.data.transactions);
    } catch (error: any) {
      Alert.alert('Unable to load transactions', error?.response?.data?.message || 'Please check your connection.');
    } finally { setLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => { loadTransactions(); }, [loadTransactions]));

  const visibleTransactions = useMemo(() => transactions.filter((item) => {
    if (filter === 'All') return true;
    if (filter === 'Pending') return ['P', 'C', 'O'].includes(item.status_code);
    if (filter === 'Completed') return item.status_code === 'D';
    if (filter === 'Cancelled') return item.status_code === 'X';
    return item.status_code === 'M';
  }), [filter, transactions]);

  const manage = async (item: Transaction, action: 'cancel' | 'delete') => {
    try {
      setActingId(item.id);
      const response = await api.post('transactions/', { appointment_id: item.id, action }, { headers: { Authorization: `Bearer ${token}` } });
      Alert.alert(action === 'cancel' ? 'Appointment cancelled' : 'Record deleted', response.data.message);
      await loadTransactions();
    } catch (error: any) {
      Alert.alert('Action unavailable', error?.response?.data?.message || 'Please try again.');
    } finally { setActingId(null); }
  };

  const confirmAction = (item: Transaction, action: 'cancel' | 'delete') => Alert.alert(
    action === 'cancel' ? 'Cancel appointment?' : 'Delete transaction?',
    action === 'cancel' ? 'This will also remove your queue reservation.' : 'This record will be permanently removed.',
    [{ text: 'Keep', style: 'cancel' }, { text: action === 'cancel' ? 'Cancel Appointment' : 'Delete', style: 'destructive', onPress: () => manage(item, action) }],
  );

  const view = (item: Transaction) => {
    if (['P', 'C', 'O'].includes(item.status_code)) return router.push('/queue');
    Alert.alert(item.service, `Appointment ID: ${item.appointment_id}\nQueue: ${item.queue_number}\nDate: ${item.appointment_date}\nTime: ${item.time_slot}\nBarangay: ${item.barangay}\nStatus: ${displayStatus(item)}`);
  };

  return <SafeAreaView style={s.safe} edges={['top']}><ScrollView style={s.page} contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
    <View style={s.hero}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable><Pressable onPress={() => router.push('/notifications')} style={s.avatar} accessibilityLabel="Open notifications"><Ionicons name="notifications-outline" size={22} color="#0646A8" /></Pressable><Text style={s.heading}>Transactions</Text><Text style={s.subheading}>Review your appointment records and service requests.</Text></View>
    <View style={s.history}>
      <View style={s.historyHead}><View style={s.historyIcon}><Ionicons name="documents-outline" size={19} color="#0759D9" /></View><View><Text style={s.historyTitle}>Appointment History</Text><Text style={s.historyCopy}>Your record of all your appointments and transactions.</Text></View><Ionicons name="calendar-outline" size={18} color="#56637C" style={s.calendar} /></View>
      <View style={s.filters}>{filters.map((item) => <Pressable key={item.label} onPress={() => setFilter(item.label)} style={[s.filter, filter === item.label && s.filterActive]}>{item.icon && <Ionicons name={item.icon} size={10} color={filter === item.label ? '#FFF' : '#34415B'} />}<Text style={[s.filterText, filter === item.label && s.filterTextActive]}>{item.label}</Text></Pressable>)}</View>
      {loading ? <ActivityIndicator style={s.loader} color="#0646A8" /> : visibleTransactions.length === 0 ? <View style={s.empty}><Ionicons name="document-text-outline" size={38} color="#9FB5DA" /><Text style={s.emptyTitle}>No {filter === 'All' ? '' : filter.toLowerCase()} transactions</Text></View> : visibleTransactions.map((item) => <TransactionCard key={item.id} item={item} disabled={actingId === item.id} onView={() => view(item)} onAction={(action) => confirmAction(item, action)} />)}
      <View style={s.reminder}><Ionicons name="information-circle-outline" size={20} color="#0759D9" /><View style={s.reminderCopy}><Text style={s.reminderTitle}>Transaction Reminder</Text><Text style={s.reminderText}>Keep a copy of your completed transactions for future reference. Documents with a claiming period should be claimed within the specified schedule.</Text></View><Ionicons name="business-outline" size={55} color="#D7E4FA" /></View>
    </View>
  </ScrollView></SafeAreaView>;
}

function displayStatus(item: Transaction) { return item.status_code === 'M' ? 'Expired' : item.status; }
function statusColors(code: string) { if (code === 'D') return ['#E5FAEC', '#159447']; if (code === 'X') return ['#FFE8EB', '#E21E31']; if (code === 'M') return ['#EEF0F4', '#596277']; if (code === 'P') return ['#FFF1DD', '#E98216']; return ['#E9F1FF', '#0759D9']; }
function TransactionCard({ item, disabled, onView, onAction }: { item: Transaction; disabled: boolean; onView: () => void; onAction: (action: 'cancel' | 'delete') => void }) {
  const [chipBg, chipText] = statusColors(item.status_code);
  const cancellable = ['P', 'C'].includes(item.status_code);
  const deletable = ['D', 'X', 'M'].includes(item.status_code);
  return <View style={s.transaction}><View style={s.transactionHead}><View style={s.documentIcon}><Ionicons name="document-text-outline" size={21} color="#0759D9" /></View><Text style={s.service}>{item.service}</Text><View style={[s.status, { backgroundColor: chipBg }]}><Ionicons name={item.status_code === 'D' ? 'checkmark-circle-outline' : item.status_code === 'P' ? 'time-outline' : 'close-circle-outline'} size={10} color={chipText} /><Text style={[s.statusText, { color: chipText }]}>{displayStatus(item)}</Text></View></View><View style={s.transactionBody}><DateDetail label="Date Booked" value={item.date_booked} /><DateDetail label="Appointment Date" value={item.appointment_date} /><DateDetail label="Date Claimed" value={item.date_claimed || '—'} /><View style={s.actions}><Pressable onPress={onView} style={[s.action, s.view]}><Ionicons name="eye-outline" size={11} color="#0759D9" /><Text style={s.viewText}>View</Text></Pressable>{cancellable && <Pressable disabled={disabled} onPress={() => onAction('cancel')} style={[s.action, s.danger]}><Ionicons name="close-circle-outline" size={11} color="#ED1C24" /><Text style={s.dangerText}>Cancel</Text></Pressable>}{deletable && <Pressable disabled={disabled} onPress={() => onAction('delete')} style={[s.action, s.danger]}><Ionicons name="trash-outline" size={11} color="#ED1C24" /><Text style={s.dangerText}>Delete</Text></Pressable>}</View></View></View>;
}
function DateDetail({ label, value }: { label: string; value: string }) { return <View style={s.dateDetail}><View style={s.dateLabel}><Ionicons name="calendar-outline" size={10} color="#233B72" /><Text style={s.dateLabelText}>{label}</Text></View><Text style={s.dateValue}>{value}</Text></View>; }

const s = StyleSheet.create({
  safe: { backgroundColor: '#07419C', flex: 1 }, page: { backgroundColor: '#F7F9FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', borderTopLeftRadius: 42, borderTopRightRadius: 42, minHeight: 158, paddingTop: 68 }, back: { left: 22, padding: 7, position: 'absolute', top: 27 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 20, height: 40, justifyContent: 'center', position: 'absolute', right: 20, top: 35, width: 40 }, heading: { color: '#FFF', fontSize: 21, fontWeight: '800' }, subheading: { color: '#FFF', fontSize: 9, marginTop: 6 }, history: { backgroundColor: '#FFF', borderTopLeftRadius: 20, borderTopRightRadius: 20, marginHorizontal: 7, marginTop: -29, minHeight: 540, padding: 12 }, historyHead: { alignItems: 'center', flexDirection: 'row' }, historyIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 10, height: 35, justifyContent: 'center', marginRight: 8, width: 35 }, historyTitle: { color: '#153573', fontSize: 11, fontWeight: '800' }, historyCopy: { color: '#6D7890', fontSize: 6, marginTop: 2 }, calendar: { marginLeft: 'auto', marginRight: 4 }, filters: { backgroundColor: '#F3F5F9', borderRadius: 6, flexDirection: 'row', marginVertical: 10, padding: 2 }, filter: { alignItems: 'center', borderRadius: 5, flex: 1, flexDirection: 'row', gap: 3, justifyContent: 'center', minHeight: 25 }, filterActive: { backgroundColor: '#0646A8' }, filterText: { color: '#34415B', fontSize: 6 }, filterTextActive: { color: '#FFF', fontWeight: '700' }, loader: { marginVertical: 55 }, empty: { alignItems: 'center', paddingVertical: 50 }, emptyTitle: { color: '#60708A', fontSize: 11, marginTop: 9 }, transaction: { borderColor: '#E2E8F2', borderRadius: 10, borderWidth: 1, marginBottom: 8, overflow: 'hidden' }, transactionHead: { alignItems: 'center', flexDirection: 'row', padding: 9 }, documentIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 7, height: 32, justifyContent: 'center', marginRight: 9, width: 32 }, service: { color: '#153573', flex: 1, fontSize: 9, fontWeight: '800' }, status: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', gap: 3, paddingHorizontal: 7, paddingVertical: 4 }, statusText: { fontSize: 6, fontWeight: '700' }, transactionBody: { alignItems: 'center', borderTopColor: '#EDF0F5', borderTopWidth: 1, flexDirection: 'row', padding: 8 }, dateDetail: { borderRightColor: '#E5EAF2', borderRightWidth: 1, flex: 1, minHeight: 33, paddingHorizontal: 5 }, dateLabel: { alignItems: 'center', flexDirection: 'row', gap: 3 }, dateLabelText: { color: '#536078', fontSize: 5.5 }, dateValue: { color: '#182B57', fontSize: 6, fontWeight: '700', marginTop: 5, textAlign: 'center' }, actions: { gap: 4, marginLeft: 6, width: 57 }, action: { alignItems: 'center', borderRadius: 4, borderWidth: 1, flexDirection: 'row', gap: 4, justifyContent: 'center', minHeight: 20 }, view: { borderColor: '#88AFE9' }, danger: { borderColor: '#FF939A' }, viewText: { color: '#0759D9', fontSize: 6 }, dangerText: { color: '#ED1C24', fontSize: 6 }, reminder: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 9, flexDirection: 'row', marginTop: 7, minHeight: 69, overflow: 'hidden', padding: 10 }, reminderCopy: { flex: 1, marginLeft: 8 }, reminderTitle: { color: '#153573', fontSize: 8, fontWeight: '800' }, reminderText: { color: '#536078', fontSize: 6, lineHeight: 9, marginTop: 3 },
});
