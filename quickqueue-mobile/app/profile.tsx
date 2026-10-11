import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { router } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { Alert, Animated, Image, KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Switch, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { SavedInformationBanner } from '@/components/SavedInformationBanner';
import { lightPalette, useAppTheme } from '@/contexts/app-theme';
import { api } from '@/services/api';
import { residentLayout } from '@/constants/resident-layout';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';
import { useConnectivity } from '@/contexts/connectivity';
import { clearCurrentResidentData, readOfflineCache, saveRecentResidentProfile, writeOfflineCache } from '@/services/offline-cache';
import { useAssistantPreference } from '@/contexts/assistant-preference';
import { useAuthSession } from '@/contexts/auth-session';
import { QuickQueueLoadingIndicator } from '@/components/QuickQueueLoadingScreen';
import { unregisterCurrentPushDevice } from '@/services/push-notifications';
import { appTypography } from '@/constants/typography';
import { clearAllBiometricLogin } from '@/services/secure-auth';

type Profile = { username: string; first_name: string; middle_name: string; last_name: string; suffix: string; created_at: string };

export default function ProfileScreen() {
  const { colors, isDark, setDarkMode } = useAppTheme();
  const { enabled: assistantEnabled, setEnabled: setAssistantEnabled } = useAssistantPreference();
  const { lock } = useAuthSession();
  const { isOnline } = useConnectivity();
  const coverHeader = useCoverHeaderScroll();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cached, setCached] = useState(false);
  const [deleteStep, setDeleteStep] = useState<'closed' | 'confirm' | 'verify' | 'success'>('closed');
  const [verificationMethod, setVerificationMethod] = useState<'password' | 'pin'>('password');
  const [credential, setCredential] = useState('');
  const [credentialVisible, setCredentialVisible] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const lastFreshLoad = useRef(0);

  useFocusEffect(useCallback(() => {
    let active = true;
    const load = async () => {
      const saved = await readOfflineCache<Profile>('profile');
      if (saved && active) { const cachedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${saved.value.username}`); setProfile(saved.value); if (cachedPhoto) setPhoto(cachedPhoto); setCached(true); setLoading(false); }
      if (!isOnline) { if (active) setLoading(false); return; }
      if (Date.now() - lastFreshLoad.current < 30000) { if (active) setLoading(false); return; }
      try {
        const token = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!token) return router.replace('/login');
        const response = await api.get<Profile>('profile/', { headers: { Authorization: `Bearer ${token}` } });
        const savedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${response.data.username}`);
        await writeOfflineCache('profile', response.data);
        if (active) { setProfile(response.data); if (savedPhoto) setPhoto(savedPhoto); setCached(false); lastFreshLoad.current = Date.now(); }
      } catch (error: any) { if (!saved) Alert.alert('Unable to load profile', error?.response?.data?.message || 'Please check your connection.'); }
      finally { if (active) setLoading(false); }
    };
    load();
    return () => { active = false; };
  }, [isOnline]));

  const logout = () => Alert.alert('Log out?', 'You will need to sign in again to access QuickQueue.', [{ text: 'Stay Signed In', style: 'cancel' }, { text: 'Log Out', style: 'destructive', onPress: async () => {
    if (!profile) return;
    await saveRecentResidentProfile({ displayName: fullName, username: profile.username });
    await unregisterCurrentPushDevice();
    await clearCurrentResidentData();
    await AsyncStorage.multiRemove(['quickqueue.accessToken', 'quickqueue.refreshToken', 'quickqueue.securitySetupStage', 'quickqueue.explicitLogout']);
    lock();
    router.replace('/welcome-back');
  } }]);

  const closeDeleteFlow = () => {
    if (deleting || deleteStep === 'success') return;
    setDeleteStep('closed');
    setCredential('');
    setDeleteError('');
    setCredentialVisible(false);
  };

  const verifyAndDelete = async () => {
    if (deleting) return;
    if (!isOnline) { setDeleteError('An internet connection is required to delete your account.'); return; }
    if (!credential || (verificationMethod === 'pin' && !/^\d{4}$/.test(credential))) {
      setDeleteError(verificationMethod === 'pin' ? 'Enter your 4-digit security PIN.' : 'Enter your current account password.');
      return;
    }
    setDeleting(true);
    setDeleteError('');
    try {
      const token = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!token) { setDeleteError('Your session has expired. Sign in again before deleting your account.'); return; }
      await api.post('account/delete/', { method: verificationMethod, credential }, { headers: { Authorization: `Bearer ${token}` } });
      setCredential('');
      setDeleteStep('success');
    } catch (error: any) {
      if (error?.response?.status === 429) setDeleteError('Too many verification attempts. Please wait before trying again.');
      else setDeleteError(error?.response?.data?.message || 'Your account could not be deleted. No changes were made.');
    } finally {
      setDeleting(false);
    }
  };

  const finishDeletion = async () => {
    await Promise.all([clearCurrentResidentData(), clearAllBiometricLogin()]);
    const keys = await AsyncStorage.getAllKeys();
    const privateKeys = keys.filter((key) => key.startsWith('quickqueue.profilePhoto.') || key.startsWith('quickqueue.cache.'));
    await AsyncStorage.multiRemove([...privateKeys, 'quickqueue.accessToken', 'quickqueue.refreshToken', 'quickqueue.securitySetupStage', 'quickqueue.pendingUsername', 'quickqueue.requiresInitialPassword', 'quickqueue.recentProfile', 'quickqueue.expoPushToken', 'quickqueue.pendingNotificationRoute', 'quickqueue.explicitLogout']);
    lock();
    setDeleteStep('closed');
    router.replace('/login');
  };
  if (loading || !profile) return <SafeAreaView style={[s.loading, { backgroundColor: colors.background }]}><QuickQueueLoadingIndicator /></SafeAreaView>;

  const middleInitial = profile.middle_name ? ` ${profile.middle_name.charAt(0).toUpperCase()}.` : '';
  const fullName = `${profile.first_name}${middleInitial} ${profile.last_name}${profile.suffix ? ` ${profile.suffix}` : ''}`;
  const memberSince = new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return <SafeAreaView style={[s.safe, { backgroundColor: '#07419C' }]} edges={['top']}><Animated.ScrollView style={{ backgroundColor: colors.background }} contentContainerStyle={s.content} showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, residentLayout.header, { justifyContent: 'center', paddingTop: 44 }, coverHeader.headerStyle]}><Pressable accessibilityLabel="Go back" onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable><HeaderNotificationBell onPress={() => router.push('/notifications')} style={s.bell} /><Text style={[s.heading, appTypography.pageTitle]}>My Profile</Text><Text style={[s.subheading, appTypography.pageSubtitle]}>View and manage your personal information.</Text></Animated.View>
    <SavedInformationBanner />
    <View style={[s.body, { backgroundColor: colors.background, marginTop: 0, paddingHorizontal: 0 }]}>
      <View style={[s.profileCard, residentLayout.overlapCard, s.responsiveCard, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, marginTop: -30 }]}><View style={[s.avatar, { backgroundColor: colors.iconBackground }]}>{photo ? <Image source={{ uri: photo }} style={s.photo} /> : <Ionicons name="person" size={43} color={colors.accent} />}</View><View style={[s.profileCopy, s.flexibleCopy]}><Text style={[s.name, { color: colors.text }]}>{fullName}</Text><Text style={[s.role, { color: colors.accent, backgroundColor: colors.iconBackground }]}>Resident</Text>{(!isOnline || cached) && <Text style={s.cached}>Saved profile · view only</Text>}<View style={s.member}><Ionicons name="calendar-outline" size={11} color={colors.muted} /><Text style={[s.memberText, { color: colors.muted }]}>Member since {memberSince}</Text></View></View></View>
      <View style={[s.menuPanel, residentLayout.card, s.responsiveCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <MenuRow icon="person-outline" title="Personal Information" subtitle="View and update your personal details and photo." onPress={() => router.push('/personal-information')} colors={colors} />
        <MenuRow icon="shield-checkmark-outline" title="Security & Login" subtitle="Manage your password and security settings." onPress={() => router.push('/security-login')} colors={colors} />
        <MenuRow icon="notifications-outline" title="Push Notifications" subtitle="Manage device permission and notification delivery." onPress={() => router.push('/notification-settings' as never)} colors={colors} />
        <MenuRow icon="globe-outline" title="Language Preferences" subtitle="Set your preferred language." onPress={() => Alert.alert('Language Preferences', 'Language options will be available soon.')} colors={colors} />
        <MenuRow icon="help-circle-outline" title="Help & Support" subtitle="Get help or contact our support team." onPress={() => Alert.alert('Help & Support', 'Please contact your barangay office for assistance.')} colors={colors} />
        <View style={[s.menuRow, { borderBottomColor: colors.border }]}><View style={[s.menuIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name="sparkles-outline" size={18} color={colors.accent} /></View><View style={s.menuCopy}><Text style={[s.menuTitle, { color: colors.text }]}>Floating AI Assistant</Text><Text style={[s.menuSubtitle, { color: colors.muted }]}>Show the assistant throughout the app.</Text></View><Switch accessibilityLabel="Floating AI Assistant" value={assistantEnabled} onValueChange={setAssistantEnabled} trackColor={{ false: '#DCE5F3', true: '#4089FF' }} thumbColor="#FFFFFF" /></View>
        <View style={[s.menuRow, { borderBottomColor: colors.border }]}><View style={[s.menuIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name="moon-outline" size={18} color={colors.accent} /></View><View style={s.menuCopy}><Text style={[s.menuTitle, { color: colors.text }]}>Dark Mode</Text><Text style={[s.menuSubtitle, { color: colors.muted }]}>Switch between light and dark mode.</Text></View><Switch value={isDark} onValueChange={setDarkMode} trackColor={{ false: '#DCE5F3', true: '#4089FF' }} thumbColor="#FFFFFF" /></View>
      </View>
      <Pressable onPress={logout} style={[s.logout, s.responsiveCard, { backgroundColor: colors.dangerBackground }]}><Ionicons name="log-out-outline" size={17} color="#FF4761" /><Text style={s.logoutText}>Log Out</Text></Pressable>
      <Pressable accessibilityRole="button" onPress={() => setDeleteStep('confirm')} style={[s.deleteButton, s.responsiveCard]}><Ionicons name="trash-outline" size={18} color="#FFFFFF" /><Text style={s.deleteButtonText}>Delete Account</Text></Pressable>
    </View>
    <Modal animationType="fade" onRequestClose={closeDeleteFlow} statusBarTranslucent transparent visible={deleteStep !== 'closed'}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={s.modalBackdrop}>
        <View accessibilityViewIsModal style={[s.modalCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          {deleteStep === 'confirm' && <>
            <View style={s.dangerIcon}><Ionicons name="trash-outline" size={28} color="#E53935" /></View>
            <Text style={[s.modalTitle, { color: colors.text }]}>Delete Account</Text>
            <Text style={[s.modalMessage, { color: colors.muted }]}>Are you sure you want to delete your account? This action is permanent and cannot be undone. All your account information and associated data will be permanently removed.</Text>
            <View style={s.modalActions}><Pressable onPress={closeDeleteFlow} style={[s.secondaryAction, { borderColor: colors.border }]}><Text style={[s.secondaryActionText, { color: colors.text }]}>No</Text></Pressable><Pressable onPress={() => setDeleteStep('verify')} style={s.dangerAction}><Text style={s.dangerActionText}>Yes</Text></Pressable></View>
          </>}
          {deleteStep === 'verify' && <>
            <Text style={[s.modalTitle, { color: colors.text }]}>Verify Your Identity</Text>
            <Text style={[s.modalMessage, { color: colors.muted }]}>For your security, please verify your identity before permanently deleting your account.</Text>
            <View style={[s.methodTabs, { backgroundColor: colors.surfaceAlt }]}><Pressable onPress={() => { setVerificationMethod('password'); setCredential(''); setDeleteError(''); }} style={[s.methodTab, verificationMethod === 'password' && s.methodTabActive]}><Text style={[s.methodText, verificationMethod === 'password' && s.methodTextActive]}>Password</Text><Text style={[s.recommended, verificationMethod === 'password' && s.recommendedActive]}>Recommended</Text></Pressable><Pressable onPress={() => { setVerificationMethod('pin'); setCredential(''); setDeleteError(''); }} style={[s.methodTab, verificationMethod === 'pin' && s.methodTabActive]}><Text style={[s.methodText, verificationMethod === 'pin' && s.methodTextActive]}>Security PIN</Text></Pressable></View>
            <Text style={[s.inputLabel, { color: colors.text }]}>{verificationMethod === 'password' ? 'Account Password' : '4-digit PIN'}</Text>
            <View style={[s.credentialField, { backgroundColor: colors.background, borderColor: deleteError ? '#E53935' : colors.border }]}><TextInput autoCapitalize="none" autoCorrect={false} keyboardType={verificationMethod === 'pin' ? 'number-pad' : 'default'} maxLength={verificationMethod === 'pin' ? 4 : undefined} onChangeText={(value) => { setCredential(verificationMethod === 'pin' ? value.replace(/\D/g, '') : value); setDeleteError(''); }} onSubmitEditing={verifyAndDelete} placeholder={verificationMethod === 'password' ? 'Enter current password' : 'Enter PIN'} placeholderTextColor={colors.muted} secureTextEntry={!credentialVisible} style={[s.credentialInput, { color: colors.text }]} value={credential} /><Pressable accessibilityLabel={credentialVisible ? 'Hide credential' : 'Show credential'} onPress={() => setCredentialVisible((value) => !value)} style={s.eye}><Ionicons name={credentialVisible ? 'eye-outline' : 'eye-off-outline'} size={21} color={colors.accent} /></Pressable></View>
            {!!deleteError && <Text accessibilityRole="alert" style={s.deleteError}>{deleteError}</Text>}
            <View style={s.modalActions}><Pressable disabled={deleting} onPress={closeDeleteFlow} style={[s.secondaryAction, { borderColor: colors.border }]}><Text style={[s.secondaryActionText, { color: colors.text }]}>Cancel</Text></Pressable><Pressable disabled={deleting} onPress={verifyAndDelete} style={[s.dangerAction, deleting && s.disabled]}><Text style={s.dangerActionText}>{deleting ? 'Verifying...' : 'Verify & Delete'}</Text></Pressable></View>
          </>}
          {deleteStep === 'success' && <>
            <View style={s.successIcon}><Ionicons name="checkmark" size={30} color="#FFFFFF" /></View>
            <Text style={[s.modalTitle, { color: colors.text }]}>Account Deleted</Text>
            <Text style={[s.modalMessage, { color: colors.muted }]}>Your account has been successfully deleted. Thank you for using QuickQueue.</Text>
            <Pressable onPress={finishDeletion} style={[s.dangerAction, s.fullAction]}><Text style={s.dangerActionText}>OK</Text></Pressable>
          </>}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  </Animated.ScrollView></SafeAreaView>;
}

function MenuRow({ icon, title, subtitle, onPress, colors }: { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle: string; onPress: () => void; colors: typeof lightPalette }) { return <Pressable onPress={onPress} style={[s.menuRow, { borderBottomColor: colors.border }]}><View style={[s.menuIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={icon} size={18} color={colors.accent} /></View><View style={[s.menuCopy, s.flexibleCopy]}><Text style={[s.menuTitle, { color: colors.text }]}>{title}</Text><Text style={[s.menuSubtitle, { color: colors.muted }]}>{subtitle}</Text></View><Ionicons name="chevron-forward" size={18} color={colors.accent} /></Pressable>; }

const s = StyleSheet.create({ responsiveCard: { alignSelf: 'center', marginHorizontal: 0, maxWidth: 600, width: '92%' }, flexibleCopy: { flexShrink: 1, minWidth: 0 }, safe: { flex: 1 }, loading: { alignItems: 'center', flex: 1, justifyContent: 'center' }, content: { flexGrow: 1, paddingBottom: 22 }, hero: { alignItems: 'center', minHeight: 150, paddingTop: 42 }, back: { left: 16, padding: 7, position: 'absolute', top: 22 }, bell: { position: 'absolute', right: 20, top: 22 }, heading: { color: '#FFF', fontSize: 24, fontWeight: '800' }, subheading: { color: '#FFF', fontSize: 12, marginTop: 7 }, body: { borderTopLeftRadius: 18, borderTopRightRadius: 18, marginTop: -18, padding: 10 }, profileCard: { alignItems: 'center', borderRadius: 15, borderWidth: 0, elevation: 2, flexDirection: 'row', minHeight: 78, paddingHorizontal: 14, paddingVertical: 8, shadowColor: '#31598A', shadowOffset: { height: 2, width: 0 }, shadowOpacity: 0.1, shadowRadius: 5 }, avatar: { alignItems: 'center', borderRadius: 24, flexShrink: 0, height: 48, justifyContent: 'center', overflow: 'hidden', width: 48 }, photo: { height: '100%', width: '100%' }, profileCopy: { flex: 1, marginLeft: 10 }, name: { flexShrink: 1, fontSize: 14, fontWeight: '600' }, role: { alignSelf: 'flex-start', borderRadius: 7, fontSize: 10, fontWeight: '500', marginTop: 2, overflow: 'hidden', paddingHorizontal: 7, paddingVertical: 2 }, cached: { color: '#D97706', fontSize: 10, fontWeight: '500', marginTop: 2 }, member: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 3 }, memberText: { flexShrink: 1, fontSize: 10 }, menuPanel: { borderRadius: 12, borderWidth: 1, marginTop: 9, overflow: 'hidden', paddingHorizontal: 9 }, menuRow: { alignItems: 'center', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 50, paddingHorizontal: 4, paddingVertical: 5 }, menuIcon: { alignItems: 'center', borderRadius: 15, flexShrink: 0, height: 30, justifyContent: 'center', marginRight: 8, width: 30 }, menuCopy: { flex: 1 }, menuTitle: { fontSize: 13, fontWeight: '600' }, menuSubtitle: { flexShrink: 1, fontSize: 10, lineHeight: 15, marginTop: 1 }, logout: { alignItems: 'center', borderRadius: 18, flexDirection: 'row', gap: 7, justifyContent: 'center', marginBottom: 8, marginTop: 9, minHeight: 42 }, logoutText: { color: '#FF4761', fontSize: 13, fontWeight: '600' }, deleteButton: { alignItems: 'center', backgroundColor: '#D92D20', borderRadius: 18, flexDirection: 'row', gap: 8, justifyContent: 'center', marginBottom: 9, minHeight: 42 }, deleteButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' }, modalBackdrop: { alignItems: 'center', backgroundColor: 'rgba(3, 15, 34, 0.62)', flex: 1, justifyContent: 'center', padding: 20 }, modalCard: { borderRadius: 20, borderWidth: 1, maxWidth: 430, padding: 22, width: '100%' }, dangerIcon: { alignItems: 'center', alignSelf: 'center', backgroundColor: '#FDECEC', borderRadius: 28, height: 56, justifyContent: 'center', marginBottom: 12, width: 56 }, successIcon: { alignItems: 'center', alignSelf: 'center', backgroundColor: '#1F9D62', borderRadius: 28, height: 56, justifyContent: 'center', marginBottom: 12, width: 56 }, modalTitle: { fontSize: 20, fontWeight: '700', textAlign: 'center' }, modalMessage: { fontSize: 13, lineHeight: 20, marginTop: 9, textAlign: 'center' }, modalActions: { flexDirection: 'row', gap: 10, marginTop: 20 }, secondaryAction: { alignItems: 'center', borderRadius: 12, borderWidth: 1, flex: 1, justifyContent: 'center', minHeight: 46 }, secondaryActionText: { fontSize: 14, fontWeight: '600' }, dangerAction: { alignItems: 'center', backgroundColor: '#D92D20', borderRadius: 12, flex: 1, justifyContent: 'center', minHeight: 46, paddingHorizontal: 10 }, dangerActionText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700', textAlign: 'center' }, fullAction: { flexGrow: 0, marginTop: 20, width: '100%' }, methodTabs: { borderRadius: 12, flexDirection: 'row', marginTop: 17, padding: 4 }, methodTab: { alignItems: 'center', borderRadius: 9, flex: 1, justifyContent: 'center', minHeight: 48, padding: 4 }, methodTabActive: { backgroundColor: '#0873FF' }, methodText: { color: '#718098', fontSize: 12, fontWeight: '600' }, methodTextActive: { color: '#FFFFFF' }, recommended: { color: '#718098', fontSize: 8 }, recommendedActive: { color: '#DCEBFF' }, inputLabel: { fontSize: 12, fontWeight: '600', marginBottom: 6, marginTop: 15 }, credentialField: { alignItems: 'center', borderRadius: 12, borderWidth: 1, flexDirection: 'row', minHeight: 50 }, credentialInput: { flex: 1, fontSize: 14, paddingHorizontal: 13, paddingVertical: 10 }, eye: { alignItems: 'center', alignSelf: 'stretch', justifyContent: 'center', paddingHorizontal: 13 }, deleteError: { color: '#D92D20', fontSize: 11, marginTop: 7 }, disabled: { opacity: 0.6 } });
