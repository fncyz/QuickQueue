import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Alert, Animated, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { useAppTheme } from '@/contexts/app-theme';
import { ConnectionStatusBanner, useConnectivity } from '@/contexts/connectivity';
import { readOfflineCache, writeOfflineCache } from '@/services/offline-cache';
import { QuickQueueLoadingIndicator } from '@/components/QuickQueueLoadingScreen';
import { appTypography } from '@/constants/typography';

type NotificationItem = { id: number; type: string; title: string; message: string; is_read: boolean; appointment_id: number; created_at: string };
type NotificationsResponse = { notifications: NotificationItem[]; pagination?: { has_more: boolean; page: number } };
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
  const { isOnline } = useConnectivity();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>('All');
  const [visibleLimit, setVisibleLimit] = useState(25);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const lastFreshLoad = useRef(0);
  const loadInFlight = useRef(false);
  const readInFlight = useRef(new Set<number>());
  const markAllInFlight = useRef(false);
  const filterScrollX = useRef(new Animated.Value(0)).current;
  const [filterViewportWidth, setFilterViewportWidth] = useState(0);
  const [filterContentWidth, setFilterContentWidth] = useState(0);

  const request = useCallback(async (method: 'get' | 'post', data?: object, url = 'notifications/') => {
    const token = await AsyncStorage.getItem('quickqueue.accessToken');
    if (!token) return router.replace('/login');
    return api.request({ method, url, data, headers: { Authorization: `Bearer ${token}` } });
  }, []);

  const load = useCallback(async () => {
    if (loadInFlight.current) return;
    loadInFlight.current = true;
    let hasCachedNotifications = false;
    try {
      const saved = await readOfflineCache<NotificationItem[]>('notifications');
      hasCachedNotifications = Boolean(saved);
      if (saved) { setItems(saved.value); setLoading(false); }
      if (!isOnline) return;
      if (Date.now() - lastFreshLoad.current < 30000) return;
      const response = await request('get', undefined, 'notifications/?page=1&page_size=50');
      if (response) {
        const data = response.data as NotificationsResponse;
        setItems(data.notifications); setPage(1); setHasMore(Boolean(data.pagination?.has_more));
        lastFreshLoad.current = Date.now(); await writeOfflineCache('notifications', data.notifications);
      }
    } catch (error: any) {
      if (!hasCachedNotifications) Alert.alert('Unable to load notifications', error?.response?.data?.message || 'Please check your connection.');
    } finally {
      loadInFlight.current = false;
      setLoading(false);
    }
  }, [isOnline, request]);

  useFocusEffect(useCallback(() => {
    setLoading(true);
    load();
  }, [load]));

  const loadMore = async () => {
    if (visibleLimit < filtered.length) { setVisibleLimit((current) => current + 25); return; }
    if (!hasMore || loadingMore || !isOnline) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const response = await request('get', undefined, `notifications/?page=${nextPage}&page_size=50`);
      if (!response) return;
      const data = response.data as NotificationsResponse;
      setItems((current) => {
        const known = new Set(current.map((item) => item.id));
        const merged = [...current, ...data.notifications.filter((item) => !known.has(item.id))];
        writeOfflineCache('notifications', merged).catch(() => undefined);
        return merged;
      });
      setPage(nextPage);
      setHasMore(Boolean(data.pagination?.has_more));
      setVisibleLimit((current) => current + 25);
    } catch (error: any) {
      Alert.alert('Unable to load more notifications', error?.response?.data?.message || 'Please try again.');
    } finally { setLoadingMore(false); }
  };

  const markRead = async (item: NotificationItem) => {
    if (!isOnline) return router.push('/queue');
    if (!item.is_read && !readInFlight.current.has(item.id)) {
      readInFlight.current.add(item.id);
      setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_read: true } : entry));
      try {
        await request('post', { notification_id: item.id });
      } catch {
        setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_read: false } : entry));
        return;
      } finally {
        readInFlight.current.delete(item.id);
      }
    }
    router.push('/queue');
  };

  const markAllRead = async () => {
    if (!isOnline) return Alert.alert('Internet connection required', 'Reconnect to update notifications.');
    if (markAllInFlight.current) return;
    markAllInFlight.current = true;
    try {
      await request('post');
      setItems((current) => current.map((item) => ({ ...item, is_read: true })));
    } catch (error: any) {
      Alert.alert('Unable to update notifications', error?.response?.data?.message || 'Please try again.');
    } finally { markAllInFlight.current = false; }
  };

  const unread = items.filter((item) => !item.is_read).length;
  const filtered = useMemo(() => items.filter((item) => filterMatches(item, filter)), [filter, items]);
  const visibleItems = filtered.slice(0, visibleLimit);
  const today = new Date().toDateString();
  const todayItems = visibleItems.filter((item) => new Date(item.created_at).toDateString() === today);
  const earlierItems = visibleItems.filter((item) => new Date(item.created_at).toDateString() !== today);
  const filters: Filter[] = ['All', 'Unread', 'Appointments', 'Queue', 'Transactions'];
  const scrollbarTrackWidth = Math.max(filterViewportWidth - 32, 0);
  const scrollbarThumbWidth = filterContentWidth > 0
    ? Math.max(32, scrollbarTrackWidth * Math.min(filterViewportWidth / filterContentWidth, 1))
    : scrollbarTrackWidth;
  const scrollbarTravel = Math.max(scrollbarTrackWidth - scrollbarThumbWidth, 0);
  const scrollableFilterDistance = Math.max(filterContentWidth - filterViewportWidth, 1);
  const scrollbarTranslateX = filterScrollX.interpolate({
    inputRange: [0, scrollableFilterDistance],
    outputRange: [0, scrollbarTravel],
    extrapolate: 'clamp',
  });
  return <SafeAreaView style={[s.safe, { backgroundColor: colors.primary }]} edges={['top', 'bottom']}>
    <View style={{ backgroundColor: colors.background }}><ConnectionStatusBanner /></View>
    <View style={[s.header, { backgroundColor: colors.primary }]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFFFFF" /></Pressable><Text style={[s.title, appTypography.pageTitle]}>Notifications</Text><View style={s.headerSpace} /></View>
    {loading ? <View style={[s.loading, { backgroundColor: colors.background }]}><QuickQueueLoadingIndicator /></View> : <ScrollView style={[s.page, { backgroundColor: colors.background }]} contentContainerStyle={s.content}>
      <Animated.ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.filterScroller} contentContainerStyle={s.filters} onLayout={(event) => setFilterViewportWidth(event.nativeEvent.layout.width)} onContentSizeChange={(width) => setFilterContentWidth(width)} onScroll={Animated.event([{ nativeEvent: { contentOffset: { x: filterScrollX } } }], { useNativeDriver: false })} scrollEventThrottle={16}>{filters.map((value) => { const count = items.filter((item) => !item.is_read && filterMatches(item, value)).length; return <Pressable key={value} onPress={() => { setFilter(value); setVisibleLimit(25); }} style={[s.filter, filter === value && s.filterActive]}><Text numberOfLines={1} style={[s.filterText, filter === value && s.filterTextActive]}>{value}</Text>{count > 0 && <View style={[s.count, filter === value && s.countActive]}><Text style={[s.countText, filter === value && s.countTextActive]}>{count}</Text></View>}</Pressable>; })}</Animated.ScrollView>
      {filterContentWidth > filterViewportWidth && <View style={s.scrollbarTrack}><Animated.View style={[s.scrollbarThumb, { width: scrollbarThumbWidth, transform: [{ translateX: scrollbarTranslateX }] }]} /></View>}
      {filtered.length === 0 ? <View style={s.empty}><Ionicons name="notifications-off-outline" size={52} color="#9DB1D3" /><Text style={s.emptyTitle}>No notifications here</Text><Text style={s.emptyText}>New appointment and queue updates will appear here.</Text></View> : <>{todayItems.length > 0 && <NotificationGroup title="Today" items={todayItems} onPress={markRead} unread={unread} onMarkAll={isOnline ? markAllRead : undefined} />}{earlierItems.length > 0 && <NotificationGroup title="Earlier" items={earlierItems} onPress={markRead} unread={todayItems.length ? undefined : unread} onMarkAll={isOnline && !todayItems.length ? markAllRead : undefined} />}</>}
      {(visibleLimit < filtered.length || hasMore) && <Pressable disabled={loadingMore} onPress={loadMore} style={[s.loadMore, { borderColor: colors.accent }]}><Text style={[s.loadMoreText, { color: colors.accent }]}>{loadingMore ? 'Loading...' : 'Load more'}</Text></Pressable>}
    </ScrollView>}
  </SafeAreaView>;
}

function NotificationGroup({ title, items, onPress, unread, onMarkAll }: { title: string; items: NotificationItem[]; onPress: (item: NotificationItem) => void; unread?: number; onMarkAll?: () => void }) {
  const { colors, isDark } = useAppTheme();
  return <View style={[s.group, s.responsiveGroup]}><View style={[s.groupHeader, s.flexibleRow]}><Text style={[s.groupTitle, { color: colors.text }]}>{title}</Text>{typeof unread === 'number' && unread > 0 && <View style={s.unreadPill}><Text style={s.unreadPillText}>{unread} unread</Text></View>}{onMarkAll && unread ? <Pressable onPress={onMarkAll} style={s.markAllButton}><Text style={s.markAll}>Mark all as read</Text></Pressable> : null}</View>{items.map((item) => { const theme = notificationTheme(item.type); return <Pressable key={item.id} onPress={() => onPress(item)} style={[s.card, { backgroundColor: item.is_read ? colors.surface : colors.surfaceAlt, borderColor: theme.color }, !item.is_read && !isDark && s.unread]}><View style={[s.icon, s.fixedItem, { backgroundColor: isDark ? theme.darkBackground : theme.background }]}><Ionicons name={theme.icon} size={21} color={theme.color} /></View><View style={[s.copy, s.flexibleCopy]}><View style={[s.row, s.flexibleRow]}><Text style={[s.cardTitle, { color: colors.text }]}>{item.title}</Text><Text style={[s.date, { color: colors.muted }]}>{formatNotificationTime(item.created_at)}</Text></View><Text style={[s.message, { color: colors.muted }]}>{item.message}</Text></View>{!item.is_read && <View style={[s.dot, s.fixedItem, { backgroundColor: theme.color }]} />}<Ionicons name="chevron-forward" size={16} color={theme.color} /></Pressable>; })}</View>;
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
  responsiveGroup: { alignSelf: 'center', maxWidth: 600, width: '100%' },
  flexibleRow: { flexWrap: 'wrap', minWidth: 0 },
  flexibleCopy: { flexShrink: 1, minWidth: 0 },
  fixedItem: { flexShrink: 0 },
  safe: { backgroundColor: '#0842A7', flex: 1 }, header: { alignItems: 'center', backgroundColor: '#0842A7', flexDirection: 'row', height: 82, justifyContent: 'space-between', paddingHorizontal: 14 }, back: { backgroundColor: '#073B96', borderRadius: 3, padding: 7 }, title: { color: '#FFFFFF', fontSize: 21, fontWeight: '800' }, headerSpace: { width: 41 }, page: { backgroundColor: '#FFFFFF', borderTopLeftRadius: 24, borderTopRightRadius: 24, flex: 1 }, content: { paddingBottom: 20, paddingTop: 10 }, filterScroller: { flexGrow: 0, height: 39, maxHeight: 39 }, filters: { alignItems: 'center', gap: 6, paddingHorizontal: 16, paddingVertical: 3 }, scrollbarTrack: { alignSelf: 'stretch', backgroundColor: '#E2E8F0', borderRadius: 2, height: 4, marginHorizontal: 16, marginTop: 6, overflow: 'hidden' }, scrollbarThumb: { backgroundColor: '#9AA4B2', borderRadius: 2, height: 4 }, filter: { alignItems: 'center', backgroundColor: '#F0F6FF', borderRadius: 15, flexDirection: 'row', gap: 4, height: 30, justifyContent: 'center', paddingHorizontal: 8, width: 110 }, filterActive: { backgroundColor: '#0750B9' }, filterText: { color: '#17447F', fontSize: 10, fontWeight: '600' }, filterTextActive: { color: '#FFFFFF' }, count: { alignItems: 'center', backgroundColor: '#1580FF', borderRadius: 8, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 3 }, countActive: { backgroundColor: '#FFFFFF' }, countText: { color: '#FFFFFF', fontSize: 10, fontWeight: '600' }, countTextActive: { color: '#0750B9' }, group: { paddingHorizontal: 16, paddingTop: 12 }, groupHeader: { alignItems: 'center', flexDirection: 'row', marginBottom: 7 }, groupTitle: { color: '#082E73', fontSize: 14, fontWeight: '600' }, unreadPill: { backgroundColor: '#E8F3FF', borderRadius: 10, marginLeft: 'auto', paddingHorizontal: 7, paddingVertical: 2 }, unreadPillText: { color: '#0873FF', fontSize: 10, fontWeight: '500' }, markAllButton: { justifyContent: 'center', marginLeft: 9, minHeight: 34 }, markAll: { color: '#0750B9', fontSize: 10, fontWeight: '600' }, loading: { alignItems: 'center', backgroundColor: '#FFFFFF', flex: 1, justifyContent: 'center' }, card: { alignItems: 'center', backgroundColor: '#FFFFFF', borderColor: '#DFE8F5', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', gap: 7, marginBottom: 5, minHeight: 52, padding: 7 }, unread: { backgroundColor: '#EDF6FF', borderColor: '#DCEBFA' }, icon: { alignItems: 'center', borderRadius: 15, height: 30, justifyContent: 'center', width: 30 }, copy: { flex: 1 }, row: { alignItems: 'center', flexDirection: 'row', gap: 5 }, cardTitle: { color: '#0D347B', flex: 1, fontSize: 13, fontWeight: '600' }, dot: { backgroundColor: '#0873FF', borderRadius: 3, height: 6, width: 6 }, message: { color: '#55709B', fontSize: 10, lineHeight: 15, marginTop: 1 }, date: { color: '#6683AF', fontSize: 10 }, empty: { alignItems: 'center', paddingHorizontal: 28, paddingTop: 100 }, emptyTitle: { color: '#19345F', fontSize: 15, fontWeight: '800', marginTop: 10 }, emptyText: { color: '#76839A', fontSize: 10, marginTop: 4, textAlign: 'center' }, loadMore: { alignItems: 'center', alignSelf: 'center', borderRadius: 18, borderWidth: 1, marginTop: 10, paddingHorizontal: 18, paddingVertical: 7 }, loadMoreText: { fontSize: 10, fontWeight: '600' },
});
