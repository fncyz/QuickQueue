import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Animated, Image, Pressable, StyleSheet, Switch, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { lightPalette, useAppTheme } from '@/contexts/app-theme';
import { api } from '@/services/api';
import { residentLayout } from '@/constants/resident-layout';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';

type Profile = { username: string; first_name: string; middle_name: string; last_name: string; suffix: string; created_at: string };

export default function ProfileScreen() {
  const { colors, isDark, setDarkMode } = useAppTheme();
  const coverHeader = useCoverHeaderScroll();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useFocusEffect(useCallback(() => {
    let active = true;
    const load = async () => {
      try {
        const token = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!token) return router.replace('/login');
        const response = await api.get<Profile>('profile/', { headers: { Authorization: `Bearer ${token}` } });
        const savedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${response.data.username}`);
        if (active) { setProfile(response.data); setPhoto(savedPhoto); }
      } catch (error: any) { Alert.alert('Unable to load profile', error?.response?.data?.message || 'Please check your connection.'); }
      finally { if (active) setLoading(false); }
    };
    load();
    return () => { active = false; };
  }, []));

  const logout = () => Alert.alert('Log out?', 'You will need to sign in again to access QuickQueue.', [{ text: 'Stay Signed In', style: 'cancel' }, { text: 'Log Out', style: 'destructive', onPress: async () => { await AsyncStorage.multiRemove(['quickqueue.accessToken', 'quickqueue.refreshToken']); router.replace('/login'); } }]);
  if (loading || !profile) return <SafeAreaView style={[s.loading, { backgroundColor: colors.background }]}><ActivityIndicator size="large" color={colors.accent} /></SafeAreaView>;

  const middleInitial = profile.middle_name ? ` ${profile.middle_name.charAt(0).toUpperCase()}.` : '';
  const fullName = `${profile.first_name}${middleInitial} ${profile.last_name}${profile.suffix ? ` ${profile.suffix}` : ''}`;
  const memberSince = new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><Animated.ScrollView style={{ backgroundColor: colors.background }} contentContainerStyle={s.content} showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, residentLayout.header, { backgroundColor: colors.primary, justifyContent: 'center', paddingTop: 44 }, coverHeader.headerStyle]}><Pressable accessibilityLabel="Go back" onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.bell} /><Text style={s.heading}>My Profile</Text><Text style={s.subheading}>View and manage your personal information.</Text></Animated.View>
    <View style={[s.body, { backgroundColor: colors.background, marginTop: 0, paddingHorizontal: 0 }]}>
      <View style={[s.profileCard, residentLayout.overlapCard, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}><View style={[s.avatar, { backgroundColor: colors.iconBackground }]}>{photo ? <Image source={{ uri: photo }} style={s.photo} /> : <Ionicons name="person" size={43} color={colors.accent} />}</View><View style={s.profileCopy}><Text style={[s.name, { color: colors.text }]}>{fullName}</Text><Text style={[s.role, { color: colors.accent, backgroundColor: colors.iconBackground }]}>Resident</Text><View style={s.member}><Ionicons name="calendar-outline" size={11} color={colors.muted} /><Text style={[s.memberText, { color: colors.muted }]}>Member since {memberSince}</Text></View></View></View>
      <View style={[s.menuPanel, residentLayout.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <MenuRow icon="person-outline" title="Personal Information" subtitle="View and update your personal details and photo." onPress={() => router.push('/personal-information')} colors={colors} />
        <MenuRow icon="shield-checkmark-outline" title="Security & Login" subtitle="Manage your password and security settings." onPress={() => router.push('/security-login')} colors={colors} />
        <MenuRow icon="notifications-outline" title="Notifications" subtitle="View your appointment and queue notifications." onPress={() => router.push('/notifications')} colors={colors} />
        <MenuRow icon="globe-outline" title="Language Preferences" subtitle="Set your preferred language." onPress={() => Alert.alert('Language Preferences', 'Language options will be available soon.')} colors={colors} />
        <MenuRow icon="help-circle-outline" title="Help & Support" subtitle="Get help or contact our support team." onPress={() => Alert.alert('Help & Support', 'Please contact your barangay office for assistance.')} colors={colors} />
        <View style={[s.menuRow, { borderBottomColor: colors.border }]}><View style={[s.menuIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name="moon-outline" size={18} color={colors.accent} /></View><View style={s.menuCopy}><Text style={[s.menuTitle, { color: colors.text }]}>Dark Mode</Text><Text style={[s.menuSubtitle, { color: colors.muted }]}>Switch between light and dark mode.</Text></View><Switch value={isDark} onValueChange={setDarkMode} trackColor={{ false: '#DCE5F3', true: '#4089FF' }} thumbColor="#FFFFFF" /></View>
      </View>
      <Pressable onPress={logout} style={[s.logout, { backgroundColor: colors.dangerBackground }]}><Ionicons name="log-out-outline" size={17} color="#FF4761" /><Text style={s.logoutText}>Log Out</Text></Pressable>
    </View>
  </Animated.ScrollView></SafeAreaView>;
}

function MenuRow({ icon, title, subtitle, onPress, colors }: { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle: string; onPress: () => void; colors: typeof lightPalette }) { return <Pressable onPress={onPress} style={[s.menuRow, { borderBottomColor: colors.border }]}><View style={[s.menuIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={icon} size={18} color={colors.accent} /></View><View style={s.menuCopy}><Text style={[s.menuTitle, { color: colors.text }]}>{title}</Text><Text style={[s.menuSubtitle, { color: colors.muted }]}>{subtitle}</Text></View><Ionicons name="chevron-forward" size={18} color={colors.accent} /></Pressable>; }

const s = StyleSheet.create({ safe: { flex: 1 }, loading: { alignItems: 'center', flex: 1, justifyContent: 'center' }, content: { flexGrow: 1, paddingBottom: 22 }, hero: { alignItems: 'center', minHeight: 150, paddingTop: 42 }, back: { left: 16, padding: 7, position: 'absolute', top: 17 }, bell: { position: 'absolute', right: 20, top: 17 }, heading: { color: '#FFF', fontSize: 24, fontWeight: '800' }, subheading: { color: '#FFF', fontSize: 12, marginTop: 7 }, body: { borderTopLeftRadius: 18, borderTopRightRadius: 18, marginTop: -18, padding: 10 }, profileCard: { alignItems: 'center', borderRadius: 15, borderWidth: 1, flexDirection: 'row', minHeight: 104, paddingHorizontal: 16 }, avatar: { alignItems: 'center', borderRadius: 34, height: 68, justifyContent: 'center', overflow: 'hidden', width: 68 }, photo: { height: '100%', width: '100%' }, profileCopy: { flex: 1, marginLeft: 14 }, name: { fontSize: 16, fontWeight: '800' }, role: { alignSelf: 'flex-start', borderRadius: 7, fontSize: 10, marginTop: 4, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3 }, member: { alignItems: 'center', flexDirection: 'row', gap: 5, marginTop: 7 }, memberText: { fontSize: 10 }, menuPanel: { borderRadius: 12, borderWidth: 1, marginTop: 12, overflow: 'hidden', paddingHorizontal: 9 }, menuRow: { alignItems: 'center', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 65, paddingHorizontal: 4 }, menuIcon: { alignItems: 'center', borderRadius: 19, height: 38, justifyContent: 'center', marginRight: 11, width: 38 }, menuCopy: { flex: 1 }, menuTitle: { fontSize: 13, fontWeight: '800' }, menuSubtitle: { fontSize: 10, lineHeight: 14, marginTop: 3 }, logout: { alignItems: 'center', borderRadius: 18, flexDirection: 'row', gap: 8, justifyContent: 'center', margin: 12, minHeight: 42 }, logoutText: { color: '#FF4761', fontSize: 13, fontWeight: '700' } });
