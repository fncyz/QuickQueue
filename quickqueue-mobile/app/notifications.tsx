import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { useAppTheme } from '@/contexts/app-theme';

type NotificationItem = { id: number; type: string; title: string; message: string; is_read: boolean; appointment_id: number; created_at: string };
type Filter = 'All' | 'Unread' | 'Appointments' | 'Queue' | 'Transactions';

const filterMatches = (item: NotificationItem, filter: Filter) => filter === 'All'
  || (filter === 'Unread' && !item.is_read)
  || (filter === 'Queue' && item.type === 'QU')
  || (filter === 'Transactions' && item.type === 'CO')
  || (filter === 'Appointments' && ['AC', 'AR', 'CA'].includes(item.type));

const notificationTheme = (type: string) => ({
  AC: { icon: 'checkmark-circle' as const, color: '#159447', background: '#DDF7EA', darkBackground: '#173B2A' },
  AR: { icon: 'calendar-outline' as const, color: '#E98216', background: '#FFF0D9', darkBackground: '#49331B' },
  QU: { icon: 'people' as const, color: '#0873FF', background: '#E0EEFF', darkBackground: '#18365C' },
  CA: { icon: 'close' as const, color: '#E21E31', background: '#FFE1E8', darkBackground: '#4A2028' },
  CO: { icon: 'checkmark-done-circle' as const, color: '#159447', background: '#DDF7EA', darkBackground: '#173B2A' },
}[type] || { icon: 'information-circle-outline' as const, color: '#0873FF', background: '#E0EEFF', darkBackground: '#18365C' });

export default function NotificationsScreen() {
  const { colors } = useAppTheme();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>('All');

  const request = useCallback(async (method: 'get' | 'post', data?: object) => {
    const token = await AsyncStorage.getItem('quickqueue.accessToken');
    if (!token) return router.replace('/login');
    return api.request({ method, url: 'notifications/', data, headers: { Authorization: `Bearer ${token}` } });
  }, []);

  const load = useCallback(async () => {
    try {
      const response = await request('get');
      if (response) setItems(response.data.notifications);
    } catch (error: any) {
      Alert.alert('Unable to load notifications', error?.response?.data?.message || 'Please check your connection.');
    } finally {
      setLoading(false);
    }
  }, [request]);

  useFocusEffect(useCallback(() => {
    setLoading(true);
    load();
  }, [load]));

  const markRead = async (item: NotificationItem) => {
    if (!item.is_read) {
      try {
        await request('post', { notification_id: item.id });
        setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_read: true } : entry));
      } catch { return; }
    }
    router.push('/queue');
  };

  const markAllRead = async () => {
    try {
      await request('post');
      setItems((current) => current.map((item) => ({ ...item, is_read: true })));
    } catch (error: any) {
      Alert.alert('Unable to update notifications', error?.response?.data?.message || 'Please try again.');
    }
  };

  const unread = items.filter((item) => !item.is_read).length;
  const filtered = useMemo(() => items.filter((item) => filterMatches(item, filter)), [filter, items]);
  const today = new Date().toDateString();
  const todayItems = filtered.filter((item) => new Date(item.created_at).toDateString() === today);
  const earlierItems = filtered.filter((item) => new Date(item.created_at).toDateString() !== today);
  const filters: Filter[] = ['All', 'Unread', 'Appointments', 'Queue', 'Transactions'];
  return <SafeAreaView style={[s.safe, { backgroundColor: colors.primary }]} edges={['top', 'bottom']}>
    <View style={[s.header, { backgroundColor: colors.primary }]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFFFFF" /></Pressable><Text style={s.title}>Notifications</Text><View style={s.headerSpace} /></View>
    {loading ? <View style={[s.loading, { backgroundColor: colors.background }]}><ActivityIndicator color={colors.accent} /></View> : <ScrollView style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.filters}>{filters.map((value) => { const count = items.filter((item) => filterMatches(item, value)).length; return <Pressable key={value} onPress={() => setFilter(value)} style={[s.filter, filter === value && s.filterActive]}><Text style={[s.filterText, filter === value && s.filterTextActive]}>{value}</Text><View style={[s.count, filter === value && s.countActive]}><Text style={[s.countText, filter === value && s.countTextActive]}>{count}</Text></View></Pressable>; })}</ScrollView>
      {filtered.length === 0 ? <View style={s.empty}><Ionicons name="notifications-off-outline" size={52} color="#9DB1D3" /><Text style={s.emptyTitle}>No notifications here</Text><Text style={s.emptyText}>New appointment and queue updates will appear here.</Text></View> : <>{todayItems.length > 0 && <NotificationGroup title="Today" items={todayItems} onPress={markRead} unread={unread} onMarkAll={markAllRead} />}{earlierItems.length > 0 && <NotificationGroup title="Earlier" items={earlierItems} onPress={markRead} unread={todayItems.length ? undefined : unread} onMarkAll={todayItems.length ? undefined : markAllRead} />}</>}
    </ScrollView>}
  </SafeAreaView>;
}

function NotificationGroup({ title, items, onPress, unread, onMarkAll }: { title: string; items: NotificationItem[]; onPress: (item: NotificationItem) => void; unread?: number; onMarkAll?: () => void }) {
  const { colors, isDark } = useAppTheme();
  return <View style={s.group}><View style={s.groupHeader}><Text style={[s.groupTitle, { color: colors.text }]}>{title}</Text>{typeof unread === 'number' && unread > 0 && <View style={s.unreadPill}><Text style={s.unreadPillText}>{unread} unread</Text></View>}{onMarkAll && unread ? <Pressable onPress={onMarkAll} style={s.markAllButton}><Text style={s.markAll}>Mark all as read</Text></Pressable> : null}</View>{items.map((item) => { const theme = notificationTheme(item.type); return <Pressable key={item.id} onPress={() => onPress(item)} style={[s.card, { backgroundColor: item.is_read ? colors.surface : colors.surfaceAlt, borderColor: theme.color }, !item.is_read && !isDark && s.unread]}><View style={[s.icon, { backgroundColor: isDark ? theme.darkBackground : theme.background }]}><Ionicons name={theme.icon} size={21} color={theme.color} /></View><View style={s.copy}><View style={s.row}><Text style={[s.cardTitle, { color: colors.text }]}>{item.title}</Text><Text style={[s.date, { color: colors.muted }]}>{formatNotificationTime(item.created_at)}</Text></View><Text style={[s.message, { color: colors.muted }]}>{item.message}</Text></View>{!item.is_read && <View style={[s.dot, { backgroundColor: theme.color }]} />}<Ionicons name="chevron-forward" size={16} color={theme.color} /></Pressable>; })}</View>;
}

function formatNotificationTime(value: string) {
  const date = new Date(value);
  const now = new Date();
  const days = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() - new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()) / 86400000);
  if (days === 0) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

const s = StyleSheet.create({
  safe: { backgroundColor: '#0842A7', flex: 1 }, header: { alignItems: 'center', backgroundColor: '#0842A7', flexDirection: 'row', height: 82, justifyContent: 'space-between', paddingHorizontal: 14 }, back: { backgroundColor: '#073B96', borderRadius: 3, padding: 7 }, title: { color: '#FFFFFF', fontSize: 21, fontWeight: '800' }, headerSpace: { width: 41 }, page: { backgroundColor: '#FFFFFF', borderTopLeftRadius: 24, borderTopRightRadius: 24, flex: 1 }, content: { paddingBottom: 20, paddingTop: 14 }, filters: { gap: 7, paddingHorizontal: 16 }, filter: { alignItems: 'center', backgroundColor: '#F0F6FF', borderRadius: 18, flexDirection: 'row', gap: 5, height: 34, paddingHorizontal: 11 }, filterActive: { backgroundColor: '#0750B9' }, filterText: { color: '#17447F', fontSize: 9, fontWeight: '700' }, filterTextActive: { color: '#FFFFFF' }, count: { alignItems: 'center', backgroundColor: '#1580FF', borderRadius: 8, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 4 }, countActive: { backgroundColor: '#FFFFFF' }, countText: { color: '#FFFFFF', fontSize: 8, fontWeight: '800' }, countTextActive: { color: '#0750B9' }, group: { paddingHorizontal: 16, paddingTop: 18 }, groupHeader: { alignItems: 'center', flexDirection: 'row', marginBottom: 10 }, groupTitle: { color: '#082E73', fontSize: 13, fontWeight: '800' }, unreadPill: { backgroundColor: '#E8F3FF', borderRadius: 11, marginLeft: 'auto', paddingHorizontal: 9, paddingVertical: 5 }, unreadPillText: { color: '#0873FF', fontSize: 8, fontWeight: '700' }, markAllButton: { marginLeft: 12 }, markAll: { color: '#0750B9', fontSize: 8, fontWeight: '700' }, loading: { alignItems: 'center', backgroundColor: '#FFFFFF', flex: 1, justifyContent: 'center' }, card: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#DFE8F5', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', gap: 11, marginBottom: 8, minHeight: 64, padding: 10 }, unread: { backgroundColor: '#EDF6FF', borderColor: '#DCEBFA' }, icon: { alignItems: 'center', borderRadius: 20, height: 40, justifyContent: 'center', width: 40 }, copy: { flex: 1 }, row: { alignItems: 'center', flexDirection: 'row', gap: 7 }, cardTitle: { color: '#0D347B', flex: 1, fontSize: 10, fontWeight: '800' }, dot: { backgroundColor: '#0873FF', borderRadius: 3, height: 6, width: 6 }, message: { color: '#55709B', fontSize: 8.5, lineHeight: 12, marginTop: 3 }, date: { color: '#6683AF', fontSize: 7.5 }, empty: { alignItems: 'center', paddingHorizontal: 28, paddingTop: 100 }, emptyTitle: { color: '#19345F', fontSize: 17, fontWeight: '800', marginTop: 14 }, emptyText: { color: '#76839A', fontSize: 12, marginTop: 6, textAlign: 'center' },
});
