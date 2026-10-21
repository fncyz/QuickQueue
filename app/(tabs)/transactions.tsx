import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Animated, AppState, Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { SavedInformationBanner } from '@/components/SavedInformationBanner';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { residentLayout } from '@/constants/resident-layout';
import { useAppTheme } from '@/contexts/app-theme';
import { useConnectivity } from '@/contexts/connectivity';
import { clearTerminalActiveAppointmentCaches, readOfflineCache, writeOfflineCache } from '@/services/offline-cache';
import { QuickQueueLoadingIndicator } from '@/components/QuickQueueLoadingScreen';
import { appTypography } from '@/constants/typography';

type Transaction = { id: number; appointment_id: string; service: string; status: string; status_code: string; status_detail?: string | null; date_booked: string; appointment_date: string; date_claimed: string | null; time_slot: string; barangay: string; queue_number: string; is_event: boolean; event_booking_id: number | null; booking_reference: string | null; event_booking_status: string | null };
type Filter = 'All' | 'Pending' | 'Completed' | 'Cancelled' | 'Expired';
type Pagination = { count: number; page: number; page_size: number; total_pages: number; next_page: number | null; previous_page: number | null };
type TransactionsResponse = { transactions: Transaction[]; pagination: Pagination };
const filters: Filter[] = ['All', 'Pending', 'Completed', 'Cancelled', 'Expired'];

const apiErrorMessage = (error: any, fallback: string) => {
  const data = error?.response?.data;
  return data?.message || data?.detail || data?.non_field_errors?.[0] || fallback;
};

export default function TransactionsScreen() {
  const { colors } = useAppTheme();
  const { isOnline } = useConnectivity();
  const coverHeader = useCoverHeaderScroll();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filter, setFilter] = useState<Filter>('All');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [actingId, setActingId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [cached, setCached] = useState(false);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const actionLock = useRef(false);
  const inFlightRequests = useRef(new Set<string>());
  const loadRevision = useRef(0);
  const screenActive = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadTransactions = useCallback(async ({ page = 1, reset = true, showLoader = true } = {}) => {
    const status = filter.toLowerCase();
    const requestKey = `${status}:${debouncedSearch}:${page}`;
    if (inFlightRequests.current.has(requestKey)) {
      setRefreshing(false);
      return;
    }
    inFlightRequests.current.add(requestKey);
    const revision = reset ? ++loadRevision.current : loadRevision.current;
    let hasCachedTransactions = false;
    if (reset) setPagination(null);
    if (reset && showLoader) setLoading(true);
    if (!reset) setLoadingMore(true);
    try {
      if (reset) {
        const saved = await readOfflineCache<Transaction[]>('transactions');
        hasCachedTransactions = Boolean(saved);
        if (saved && revision === loadRevision.current) {
          setTransactions(saved.value);
          setCached(true);
          if (showLoader) setLoading(false);
        }
      }
      if (!isOnline) return;
      const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) return router.replace('/login');
      setToken(accessToken);
      const response = await api.get<TransactionsResponse>('transactions/', {
        headers: { Authorization: `Bearer ${accessToken}` },
        params: { paginate: 1, page, q: debouncedSearch || undefined, status },
      });
      if (revision !== loadRevision.current) return;
      if (reset) {
        setTransactions(response.data.transactions);
        if (status === 'all' && !debouncedSearch) {
          await writeOfflineCache('transactions', response.data.transactions);
        }
      } else {
        setTransactions((current) => {
          const merged = Array.from(
            new Map([...current, ...response.data.transactions].map((item) => [item.id, item])).values(),
          );
          if (status === 'all' && !debouncedSearch) {
            writeOfflineCache('transactions', merged).catch(() => undefined);
          }
          return merged;
        });
      }
      setPagination(response.data.pagination);
      setCached(false);
      await clearTerminalActiveAppointmentCaches(
        response.data.transactions
          .filter((item: Transaction) => !item.is_event && ['D', 'X', 'M'].includes(item.status_code))
          .map((item: Transaction) => item.appointment_id),
      );
    } catch (error: any) {
      if (reset && !hasCachedTransactions && revision === loadRevision.current) Alert.alert('Unable to load transactions', error?.response?.data?.message || 'Please check your connection.');
    } finally {
      inFlightRequests.current.delete(requestKey);
      if (revision === loadRevision.current) {
        setLoading(false);
        setRefreshing(false);
        setLoadingMore(false);
      }
    }
  }, [debouncedSearch, filter, isOnline]);

  useFocusEffect(useCallback(() => {
    screenActive.current = true;
    loadTransactions();
    return () => { screenActive.current = false; };
  }, [loadTransactions]));

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active' && screenActive.current) loadTransactions();
    });
    return () => subscription.remove();
  }, [loadTransactions]);

  const filteredTransactions = useMemo(() => transactions.filter((item) => {
    const matchesFilter = filter === 'All' || (filter === 'Pending' && ['P', 'C', 'O'].includes(item.status_code)) || (filter === 'Completed' && item.status_code === 'D') || (filter === 'Cancelled' && item.status_code === 'X') || (filter === 'Expired' && item.status_code === 'M');
    const query = search.trim().toLowerCase();
    return matchesFilter && (!query || item.service.toLowerCase().includes(query) || item.appointment_id.toLowerCase().includes(query) || item.queue_number.toLowerCase().includes(query));
  }), [filter, search, transactions]);

  const loadMore = useCallback(() => {
    if (!isOnline || loading || loadingMore || !pagination?.next_page) return;
    void loadTransactions({ page: pagination.next_page, reset: false, showLoader: false });
  }, [isOnline, loadTransactions, loading, loadingMore, pagination?.next_page]);

  const refresh = useCallback(() => {
    if (refreshing) return;
    setRefreshing(true);
    void loadTransactions({ page: 1, reset: true, showLoader: false });
  }, [loadTransactions, refreshing]);

  const manage = async (item: Transaction, action: 'cancel' | 'delete') => {
    if (!isOnline) return Alert.alert('Internet connection required', 'Reconnect to manage this transaction.');
    if (actionLock.current) return;
    actionLock.current = true;
    try {
      setActingId(item.id);
      const accessToken = token || await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) {
        router.replace('/login');
        return;
      }
      const response = await api.post<{ success: boolean; message: string }>('transactions/', { appointment_id: item.id, action }, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (response.data.success !== true) throw new Error('The server did not confirm this action.');
      const updated = action === 'delete'
        ? transactions.filter((transaction) => transaction.id !== item.id)
        : transactions.map((transaction) => transaction.id === item.id ? { ...transaction, status: 'Cancelled', status_code: 'X' } : transaction);
      setTransactions(updated);
      setCached(false);
      writeOfflineCache('transactions', updated).catch(() => undefined);
      Alert.alert(action === 'cancel' ? 'Appointment cancelled' : 'Record deleted', response.data.message);
    } catch (error: any) {
      Alert.alert(action === 'cancel' ? 'Unable to cancel appointment' : 'Unable to delete transaction', apiErrorMessage(error, error?.message || 'Please try again.'));
    } finally { actionLock.current = false; setActingId(null); }
  };

  const confirmAction = (item: Transaction, action: 'cancel' | 'delete') => Alert.alert(
    action === 'cancel' ? 'Cancel appointment?' : 'Delete transaction?',
    action === 'cancel' ? 'This will also remove your queue reservation.' : 'This record will be permanently removed.',
    [{ text: 'Keep', style: 'cancel' }, { text: action === 'cancel' ? 'Cancel Appointment' : 'Delete', style: 'destructive', onPress: () => manage(item, action) }],
  );

  const view = (item: Transaction) => {
    if (item.is_event && item.event_booking_id) return router.push({ pathname: '/event-pass' as never, params: { bookingId: String(item.event_booking_id) } });
    if (['P', 'C', 'O'].includes(item.status_code)) return router.push('/queue');
    Alert.alert(item.service, `Appointment ID: ${item.appointment_id}\nQueue: ${item.queue_number}\nDate: ${item.appointment_date}\nTime: ${item.time_slot}\nBarangay: ${item.barangay}\nStatus: ${displayStatus(item)}`);
  };

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><Animated.FlatList
    data={filteredTransactions}
    keyExtractor={(item) => String(item.id)}
    renderItem={({ item }) => <TransactionCard item={item} disabled={actingId === item.id || !isOnline} onView={() => view(item)} onAction={(action) => confirmAction(item, action)} />}
    style={[s.page, { backgroundColor: colors.background }]}
    contentContainerStyle={s.content}
    keyboardDismissMode="on-drag"
    keyboardShouldPersistTaps="handled"
    showsVerticalScrollIndicator={false}
    onScroll={coverHeader.onScroll}
    scrollEventThrottle={16}
    onEndReached={loadMore}
    onEndReachedThreshold={0.35}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} colors={[colors.accent]} />}
    ListHeaderComponent={<>
    <Animated.View style={[s.hero, coverHeader.headerStyle]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={26} color="#FFF" /></Pressable><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.avatar} /><Text numberOfLines={2} style={s.heading}>Transactions</Text><Text numberOfLines={2} style={s.subheading}>Review your appointment records and service requests.</Text></Animated.View>
    <SavedInformationBanner />
    <View style={[s.history, s.historyControls, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={s.historyHead}><View style={[s.historyIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name="documents-outline" size={19} color={colors.accent} /></View><View style={{ flex: 1, minWidth: 0 }}><Text style={[s.historyTitle, { color: colors.text }]}>Appointment History</Text><Text fixedFontSize={10} numberOfLines={2} style={[s.historyCopy, { color: colors.muted }]}>{!isOnline || cached ? 'Saved history · statuses may not be up to date.' : 'Your record of all your appointments and transactions.'}</Text></View></View>
      <View style={[s.search, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><Ionicons name="search" size={16} color={colors.muted} /><TextInput fixedFontSize={10} value={search} onChangeText={setSearch} placeholder="Search service or reference number" placeholderTextColor={colors.muted} style={[s.searchInput, { color: colors.text }]} /></View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.filterScroller} contentContainerStyle={s.filters}>{filters.map((item) => <Pressable key={item} onPress={() => setFilter(item)} style={[s.filter, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }, filter === item && s.filterActive]}><Text numberOfLines={1} style={[s.filterText, { color: colors.text }, filter === item && s.filterTextActive]}>{item}</Text></Pressable>)}</ScrollView>
    </View>
    </>}
    ListEmptyComponent={loading ? <View style={s.loader}><QuickQueueLoadingIndicator size={60} /></View> : <View style={s.empty}><Ionicons name="document-text-outline" size={38} color="#9FB5DA" /><Text style={s.emptyTitle}>No {filter === 'All' ? '' : filter.toLowerCase()} transactions</Text></View>}
    ListFooterComponent={<View style={s.transactionListFooter}>{loadingMore && <View style={s.loadMoreIndicator}><QuickQueueLoadingIndicator size={42} /></View>}<View style={[s.reminder, { backgroundColor: colors.surfaceAlt }]}><Ionicons name="information-circle-outline" size={20} color={colors.accent} /><View style={s.reminderCopy}><Text style={[s.reminderTitle, { color: colors.text }]}>Transaction Reminder</Text><Text style={[s.reminderText, { color: colors.muted }]}>Keep a copy of completed transactions. Claim documents within the scheduled period.</Text></View><Ionicons name="business-outline" size={55} color={colors.border} /></View></View>}
  /></SafeAreaView>;
}

function displayStatus(item: Transaction) { if (item.is_event) return item.event_booking_status === 'checked_in' ? 'Checked In' : item.event_booking_status === 'cancelled' ? 'Cancelled' : item.event_booking_status === 'event_ended' ? 'Event Ended' : 'Confirmed'; return item.status_code === 'M' ? 'Expired' : item.status; }
function displayStatusDetail(item: Transaction) { return item.status_detail || null; }
function statusColors(code: string) { if (code === 'D') return ['#E5FAEC', '#159447']; if (code === 'X') return ['#FFE8EB', '#E21E31']; if (code === 'M') return ['#EEF0F4', '#596277']; if (code === 'P') return ['#FFF1DD', '#E98216']; return ['#E9F1FF', '#0759D9']; }
function statusIcon(code: string) {
  if (code === 'D' || code === 'C') return 'checkmark-circle-outline' as const;
  if (code === 'X') return 'close-circle-outline' as const;
  return 'time-outline' as const;
}
const TransactionCard = memo(function TransactionCard({ item, disabled, onView, onAction }: { item: Transaction; disabled: boolean; onView: () => void; onAction: (action: 'cancel' | 'delete') => void }) {
  const { colors } = useAppTheme();
  const [chipBg, chipText] = statusColors(item.status_code);
  const cancellable = ['P', 'C'].includes(item.status_code);
  const deletable = !item.is_event && ['D', 'X', 'M'].includes(item.status_code);
  const statusDetail = displayStatusDetail(item);
  return <View style={[s.transaction, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }, disabled && s.disabledCard]}>
    <View style={s.transactionHead}>
      <View style={s.serviceGroup}><View style={[s.documentIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={item.is_event ? 'ticket-outline' : 'document-text-outline'} size={20} color={colors.accent} /></View><View style={{ flex: 1, minWidth: 0 }}>{item.is_event && <Text style={s.eventBadge}>EVENT</Text>}<Text fixedFontSize={13} style={[s.service, { color: colors.text }]}>{item.service}</Text></View></View>
      <View style={s.statusGroup}><View style={[s.status, { backgroundColor: chipBg }]}><Ionicons name={statusIcon(item.status_code)} size={13} color={chipText} /><Text fixedFontSize={10} style={[s.statusText, { color: chipText }]}>{displayStatus(item)}</Text></View>{statusDetail && <Text fixedFontSize={9} style={[s.statusDetail, { color: colors.muted }]}>{statusDetail}</Text>}</View>
    </View>
    <View style={[s.transactionBody, { borderTopColor: colors.border }]}>
      <View style={s.details}><DateDetail label="Date Booked" value={item.date_booked} /><DateDetail label="Appointment Date" value={item.appointment_date} /><DateDetail label="Date Claimed" value={item.date_claimed || '—'} /></View>
      <View style={s.actions}><Pressable onPress={onView} style={[s.action, s.view]}><Ionicons name="eye-outline" size={17} color={colors.accent} /><Text fixedFontSize={12} style={[s.viewText, { color: colors.accent }]}>View</Text></Pressable>{cancellable && <Pressable disabled={disabled} onPress={() => onAction('cancel')} style={[s.action, s.danger, disabled && s.disabledAction]}><Ionicons name="close-circle-outline" size={17} color="#ED1C24" /><Text fixedFontSize={12} style={s.dangerText}>Cancel</Text></Pressable>}{deletable && <Pressable disabled={disabled} onPress={() => onAction('delete')} style={[s.action, s.danger, disabled && s.disabledAction]}><Ionicons name="trash-outline" size={17} color="#ED1C24" /><Text fixedFontSize={12} style={s.dangerText}>Delete</Text></Pressable>}</View>
    </View>
  </View>;
});
function DateDetail({ label, value }: { label: string; value: string }) { const { colors } = useAppTheme(); return <View style={s.dateDetail}><Ionicons name="calendar-outline" size={15} color={colors.accent} /><View style={s.dateCopy}><Text fixedFontSize={10} style={[s.dateLabelText, { color: colors.muted }]}>{label}</Text><Text fixedFontSize={12} style={[s.dateValue, { color: colors.text }]}>{value}</Text></View></View>; }

const readableStyles = {
  heading: { ...appTypography.pageTitle, color: '#FFF', maxWidth: '76%', textAlign: 'center' }, subheading: { ...appTypography.pageSubtitle, color: '#FFF', marginTop: 5, maxWidth: '88%', textAlign: 'center' }, historyIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 9, height: 34, justifyContent: 'center', marginRight: 8, width: 34 }, historyCopyContainer: { flex: 1, minWidth: 0 }, historyTitle: { color: '#153573', fontSize: 15, fontWeight: '700', lineHeight: 20 }, historyCopy: { color: '#6D7890', fontSize: 12, lineHeight: 16, marginTop: 2 },
  filter: { alignItems: 'center', borderRadius: 5, flex: 1, flexDirection: 'row', gap: 3, justifyContent: 'center', minHeight: 32 }, filterText: { color: '#34415B', fontSize: 10 }, transactionHead: { alignItems: 'center', flexDirection: 'row', padding: 8 }, documentIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 7, height: 32, justifyContent: 'center', marginRight: 8, width: 32 }, service: { color: '#153573', flex: 1, fontSize: 13, fontWeight: '600' }, statusText: { fontSize: 10, fontWeight: '600' },
  transactionBody: { alignItems: 'stretch', borderTopColor: '#EDF0F5', borderTopWidth: 1, flexDirection: 'row', flexWrap: 'wrap', padding: 8 }, dateDetail: { borderRightColor: '#E5EAF2', borderRightWidth: 1, flexBasis: 82, flexGrow: 1, minHeight: 42, paddingHorizontal: 5 }, dateLabelText: { color: '#536078', fontSize: 10, fontWeight: '500' }, dateValue: { color: '#182B57', fontSize: 10, fontWeight: '600', marginTop: 2, textAlign: 'center' }, actions: { flexBasis: 78, flexGrow: 1, gap: 4, marginLeft: 6 }, action: { alignItems: 'center', borderRadius: 4, borderWidth: 1, flexDirection: 'row', gap: 4, justifyContent: 'center', minHeight: 32 }, viewText: { color: '#0759D9', fontSize: 10, fontWeight: '600' }, dangerText: { color: '#ED1C24', fontSize: 10, fontWeight: '600' }, reminderTitle: { color: '#153573', fontSize: 14, fontWeight: '600' }, reminderText: { color: '#536078', fontSize: 10, lineHeight: 16, marginTop: 2 },
} as const;

const s = StyleSheet.create({
  safe: { backgroundColor: '#07419C', flex: 1 }, page: { backgroundColor: '#F7F9FD', flex: 1 }, content: { paddingBottom: 18 }, hero: { alignItems: 'center', backgroundColor: '#07419C', minHeight: 158, paddingTop: 68 }, back: { left: 22, padding: 7, position: 'absolute', top: 27 }, avatar: { alignItems: 'center', backgroundColor: '#FFF', borderRadius: 20, height: 40, justifyContent: 'center', position: 'absolute', right: 20, top: 35, width: 40 }, heading: { color: '#FFF', fontSize: 21, fontWeight: '800' }, subheading: { color: '#FFF', fontSize: 9, marginTop: 6 }, history: { backgroundColor: '#FFF', borderTopLeftRadius: 20, borderTopRightRadius: 20, marginHorizontal: 7, marginTop: -29, minHeight: 540, padding: 12 }, historyHead: { alignItems: 'center', flexDirection: 'row' }, historyIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 10, height: 35, justifyContent: 'center', marginRight: 8, width: 35 }, historyTitle: { color: '#153573', fontSize: 11, fontWeight: '800' }, historyCopy: { color: '#6D7890', fontSize: 6, marginTop: 2 }, calendar: { marginLeft: 'auto', marginRight: 4 }, filters: { backgroundColor: '#F3F5F9', borderRadius: 6, flexDirection: 'row', marginVertical: 10, padding: 2 }, filter: { alignItems: 'center', borderRadius: 5, flex: 1, flexDirection: 'row', gap: 3, justifyContent: 'center', minHeight: 25 }, filterActive: { backgroundColor: '#0646A8' }, filterText: { color: '#34415B', fontSize: 6 }, filterTextActive: { color: '#FFF', fontWeight: '700' }, loader: { alignItems: 'center', justifyContent: 'center', minHeight: 300, width: '100%' }, empty: { alignItems: 'center', paddingVertical: 50 }, emptyTitle: { color: '#60708A', fontSize: 11, marginTop: 9 }, transaction: { borderColor: '#E2E8F2', borderRadius: 10, borderWidth: 1, marginBottom: 8, overflow: 'hidden' }, transactionHead: { alignItems: 'center', flexDirection: 'row', padding: 9 }, documentIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 7, height: 32, justifyContent: 'center', marginRight: 9, width: 32 }, service: { color: '#153573', flex: 1, fontSize: 9, fontWeight: '800' }, status: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', gap: 3, paddingHorizontal: 7, paddingVertical: 4 }, statusText: { fontSize: 6, fontWeight: '700' }, transactionBody: { alignItems: 'center', borderTopColor: '#EDF0F5', borderTopWidth: 1, flexDirection: 'row', padding: 8 }, dateDetail: { borderRightColor: '#E5EAF2', borderRightWidth: 1, flex: 1, minHeight: 33, paddingHorizontal: 5 }, dateLabel: { alignItems: 'center', flexDirection: 'row', gap: 3 }, dateLabelText: { color: '#536078', fontSize: 5.5 }, dateValue: { color: '#182B57', fontSize: 6, fontWeight: '700', marginTop: 5, textAlign: 'center' }, actions: { gap: 4, marginLeft: 6, width: 57 }, action: { alignItems: 'center', borderRadius: 4, borderWidth: 1, flexDirection: 'row', gap: 4, justifyContent: 'center', minHeight: 20 }, view: { borderColor: '#88AFE9' }, danger: { borderColor: '#FF939A' }, viewText: { color: '#0759D9', fontSize: 6 }, dangerText: { color: '#ED1C24', fontSize: 6 }, reminder: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 9, flexDirection: 'row', marginTop: 'auto', minHeight: 69, overflow: 'hidden', padding: 10 }, reminderCopy: { flex: 1, marginLeft: 8 }, reminderTitle: { color: '#153573', fontSize: 8, fontWeight: '800' }, reminderText: { color: '#536078', fontSize: 6, lineHeight: 9, marginTop: 3 },
  search: { alignItems: 'center', borderColor: '#DCE4F1', borderRadius: 9, borderWidth: 1, flexDirection: 'row', gap: 8, marginBottom: 10, marginTop: 7, minHeight: 40, paddingHorizontal: 11 },
  searchInput: { color: '#182B57', flex: 1, fontSize: 9 },
  filterScroller: { flexGrow: 0, height: 45, maxHeight: 45 },
  disabledCard: { opacity: 0.82 },
  disabledAction: { opacity: 0.35 },
  loadMore: { alignItems: 'center', alignSelf: 'center', borderRadius: 18, borderWidth: 1, marginBottom: 8, paddingHorizontal: 22, paddingVertical: 9 },
  loadMoreText: { fontSize: 11, fontWeight: '700' },
  serviceGroup: { alignItems: 'center', flex: 1, flexDirection: 'row', minWidth: 0 },
  statusGroup: { alignItems: 'flex-end' },
  statusDetail: { fontSize: 9, textAlign: 'right' },
  details: { gap: 7 },
  eventBadge: { color: '#A45A00', fontSize: 8, fontWeight: '900', letterSpacing: 0.8, marginBottom: 2 },
  dateCopy: { flex: 1, minWidth: 0 },
  historyControls: { flexGrow: 0, marginBottom: 10, minHeight: 0 },
  transactionListFooter: { alignSelf: 'center', maxWidth: 600, paddingHorizontal: 12, width: '92%' },
  loadMoreIndicator: { alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  ...(readableStyles as Record<string, object>),
  ...({
    hero: { ...residentLayout.header, alignItems: 'center', justifyContent: 'center', paddingTop: 44 },
    history: { ...residentLayout.overlapCard, alignSelf: 'center', backgroundColor: '#FFF', flexGrow: 1, marginHorizontal: 0, maxWidth: 600, padding: 12, width: '92%' },
    historyControls: { flexGrow: 0, marginBottom: 10, minHeight: 0 },
    filters: { alignItems: 'center', flexDirection: 'row', gap: 6, paddingHorizontal: 1, paddingVertical: 4 },
    filter: { alignItems: 'center', borderRadius: 18, borderWidth: 1, height: 34, justifyContent: 'center', minWidth: 76, paddingHorizontal: 12 },
    filterActive: { backgroundColor: '#0646A8', borderColor: '#0646A8' },
    filterText: { color: '#34415B', fontSize: 10, fontWeight: '600' },
    historyHead: { alignItems: 'center', flexDirection: 'row', minWidth: 0, width: '100%' },
    transaction: { alignSelf: 'center', borderColor: '#E2E8F2', borderRadius: 16, borderWidth: 1, marginBottom: 10, maxWidth: 560, overflow: 'hidden', width: '92%' },
    transactionListFooter: { alignSelf: 'center', maxWidth: 600, paddingHorizontal: 12, width: '92%' },
    loadMoreIndicator: { alignItems: 'center', minHeight: 52, justifyContent: 'center' },
    transactionHead: { alignItems: 'flex-start', flexDirection: 'row', minHeight: 62, minWidth: 0, paddingHorizontal: 12, paddingVertical: 10 },
    serviceGroup: { alignItems: 'center', flex: 1, flexDirection: 'row', minWidth: 0, paddingRight: 8 },
    documentIcon: { alignItems: 'center', backgroundColor: '#EDF3FF', borderRadius: 10, flexShrink: 0, height: 40, justifyContent: 'center', marginRight: 9, width: 40 },
    service: { color: '#153573', flex: 1, flexShrink: 1, fontSize: 13, fontWeight: '700', lineHeight: 18, minWidth: 0 },
    statusGroup: { alignItems: 'flex-end', flexShrink: 0, maxWidth: '42%' },
    status: { alignItems: 'center', borderRadius: 13, flexDirection: 'row', gap: 4, paddingHorizontal: 9, paddingVertical: 5 },
    statusText: { fontSize: 10, fontWeight: '600', lineHeight: 13 },
    statusDetail: { fontSize: 9, lineHeight: 13, marginTop: 3, textAlign: 'right' },
    transactionBody: { alignItems: 'stretch', borderTopColor: '#EDF0F5', borderTopWidth: 1, flexDirection: 'column', paddingHorizontal: 11, paddingVertical: 9 },
    details: { gap: 7, minWidth: 0 },
    dateDetail: { alignItems: 'center', flexDirection: 'row', minHeight: 25, minWidth: 0, paddingHorizontal: 2 },
    dateCopy: { alignItems: 'center', flex: 1, flexDirection: 'row', marginLeft: 8, minWidth: 0 },
    dateLabelText: { color: '#536078', fontSize: 9, fontWeight: '500', lineHeight: 12 },
    dateValue: { color: '#182B57', flexShrink: 1, fontSize: 11, fontWeight: '600', lineHeight: 16, marginLeft: 10, textAlign: 'left' },
    actions: { flexDirection: 'row', gap: 8, marginTop: 10, width: '100%' },
    action: { alignItems: 'center', borderRadius: 7, borderWidth: 1, flex: 1, flexDirection: 'row', gap: 6, justifyContent: 'center', minHeight: 38, paddingHorizontal: 8 },
    viewText: { color: '#0759D9', fontSize: 11, fontWeight: '600' },
    dangerText: { color: '#ED1C24', fontSize: 11, fontWeight: '600' },
  } as Record<string, object>),
});
