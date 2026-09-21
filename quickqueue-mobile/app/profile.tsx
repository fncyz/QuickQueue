import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Animated, Pressable, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, changePassword } from '@/services/api';
import { HeaderNotificationBell } from '@/components/HeaderNotificationBell';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';

type Profile = { username: string; first_name: string; middle_name: string; last_name: string; suffix: string; birthdate: string; sex_display: string; email: string | null; contact_number: string; province: string; municipality: string; barangay: string; age: number; created_at: string };

const profileReadableStyles = StyleSheet.create({
  heading: { color: '#FFF', fontSize: 24, fontWeight: '800' }, subheading: { color: '#FFF', fontSize: 12, marginTop: 7 },
  profileCard: { alignItems: 'center', backgroundColor: '#EAF4FF', borderColor: '#CFE2FA', borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 104, paddingHorizontal: 16 }, name: { color: '#10295E', fontSize: 16, fontWeight: '800' }, role: { alignSelf: 'flex-start', backgroundColor: '#D3E8FF', borderRadius: 7, color: '#0759D9', fontSize: 10, marginTop: 4, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3 }, memberText: { color: '#667FA8', fontSize: 10 },
  menuRow: { alignItems: 'center', borderBottomColor: '#E8ECF3', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 65, paddingHorizontal: 4 }, menuIconSmall: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 19, height: 38, justifyContent: 'center', marginRight: 11, width: 38 }, menuTitle: { color: '#10295E', fontSize: 13, fontWeight: '800' }, menuSubtitle: { color: '#718098', fontSize: 10, lineHeight: 14, marginTop: 3 },
  editInput: { backgroundColor: '#F7F9FD', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#152654', fontSize: 12, height: 42, paddingHorizontal: 10 }, saveText: { color: '#FFF', fontSize: 12, fontWeight: '800' }, passwordLabel: { color: '#26385D', fontSize: 11, fontWeight: '700', marginBottom: 5 }, passwordInput: { backgroundColor: '#FFF', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#152654', fontSize: 12, height: 42, paddingHorizontal: 10 }, logoutText: { color: '#FF4761', fontSize: 13, fontWeight: '700' }, privacyTitle: { color: '#0759D9', fontSize: 11, fontWeight: '800' }, privacyText: { color: '#718098', fontSize: 9, lineHeight: 13, marginTop: 2 },
});

export default function ProfileScreen() {
  Object.assign(s, profileReadableStyles);
  const coverHeader = useCoverHeaderScroll();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState('');
  const [contact, setContact] = useState('');
  const [securityOpen, setSecurityOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  const loadProfile = async () => {
    try {
      const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
      if (!accessToken) return router.replace('/login');
      setToken(accessToken);
      const response = await api.get<Profile>('profile/', { headers: { Authorization: `Bearer ${accessToken}` } });
      setProfile(response.data); setEmail(response.data.email || ''); setContact(response.data.contact_number);
    } catch (error: any) {
      Alert.alert('Unable to load profile', error?.response?.data?.message || 'Please check your connection.');
    } finally { setLoading(false); }
  };
  useEffect(() => { loadProfile(); }, []);

  const saveProfile = async () => {
    if (!contact.trim()) return Alert.alert('Contact number required', 'Enter your contact number.');
    try {
      setSaving(true);
      const response = await api.patch<Profile>('profile/', { email, contact_number: contact }, { headers: { Authorization: `Bearer ${token}` } });
      setProfile(response.data); setEditing(false); Alert.alert('Profile updated', 'Your contact information has been saved.');
    } catch (error: any) { Alert.alert('Profile not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  const updatePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) return Alert.alert('Missing information', 'Complete all password fields.');
    try {
      setSaving(true); await changePassword(token, currentPassword, newPassword, confirmPassword);
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword(''); setSecurityOpen(false); Alert.alert('Password updated', 'Use your new password the next time you sign in.');
    } catch (error: any) { Alert.alert('Password not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  const logout = () => Alert.alert('Log out?', 'You will need to sign in again to access QuickQueue.', [{ text: 'Stay Signed In', style: 'cancel' }, { text: 'Log Out', style: 'destructive', onPress: async () => { await AsyncStorage.multiRemove(['quickqueue.accessToken', 'quickqueue.refreshToken']); router.replace('/login'); } }]);
  if (loading || !profile) return <SafeAreaView style={s.loading}><ActivityIndicator size="large" color="#0646A8" /></SafeAreaView>;

  const middleInitial = profile.middle_name ? ` ${profile.middle_name.charAt(0).toUpperCase()}.` : '';
  const fullName = `${profile.first_name}${middleInitial} ${profile.last_name}${profile.suffix ? ` ${profile.suffix}` : ''}`;
  const memberSince = new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return <SafeAreaView style={[s.safe, { backgroundColor: '#FFFFFF' }]} edges={['top']}>
    <Animated.ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled" onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
      <Animated.View style={[s.hero, coverHeader.headerStyle]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFF" /></Pressable><HeaderNotificationBell onPress={() => router.push('/notifications')} style={{ position: 'absolute', right: 20, top: 17 }} /><Text style={s.heading}>My Profile</Text><Text style={s.subheading}>View and manage your personal information.</Text></Animated.View>
      <View style={s.body}>
        <View style={s.profileCard}><View style={s.avatarOuter}><View style={s.avatar}><Ionicons name="person" size={48} color="#77A0EE" /></View><View style={s.camera}><Ionicons name="camera" size={9} color="#FFF" /></View></View><View style={s.profileCopy}><Text style={s.name}>{fullName}</Text><Text style={s.role}>Resident</Text><View style={s.member}><Ionicons name="calendar-outline" size={10} color="#667FA8" /><Text style={s.memberText}>Member since {memberSince}</Text></View></View><Ionicons name="chevron-forward" size={18} color="#4F75B4" /></View>

        <View style={s.menuPanel}>
          <MenuRow icon="person-outline" title="Personal Information" subtitle="View and update your personal details." onPress={() => router.push('/personal-information')} />
          <MenuRow icon="id-card-outline" title="Account Information" subtitle="View your account details." onPress={() => setEditing((value) => !value)} />
          <MenuRow icon="shield-checkmark-outline" title="Security & Login" subtitle="Manage your password and security settings." onPress={() => setSecurityOpen((value) => !value)} />
          <MenuRow icon="notifications-outline" title="Notifications" subtitle="Manage your notification preferences." onPress={() => router.push('/notifications')} />
          <MenuRow icon="globe-outline" title="Language Preferences" subtitle="Set your preferred language." onPress={() => Alert.alert('Language Preferences', 'Language options will be available soon.')} />
          <MenuRow icon="help-circle-outline" title="Help & Support" subtitle="Get help or contact our support team." onPress={() => Alert.alert('Help & Support', 'Please contact your barangay office for assistance.')} />
          <View style={s.menuRow}><View style={s.menuIconSmall}><Ionicons name="moon-outline" size={18} color="#0759D9" /></View><View style={s.menuCopy}><Text style={s.menuTitle}>Dark Mode</Text><Text style={s.menuSubtitle}>Switch between light and dark mode.</Text></View><Switch value={darkMode} onValueChange={setDarkMode} trackColor={{ false: '#DCE5F3', true: '#4089FF' }} thumbColor="#FFFFFF" /></View>
        </View>

        {editing && <View style={s.infoCard}><EditRow icon="call-outline" label="Contact Number" value={contact} onChangeText={setContact} keyboardType="phone-pad" /><EditRow icon="mail-outline" label="Email Address" value={email} onChangeText={setEmail} keyboardType="email-address" /><Pressable disabled={saving} onPress={saveProfile} style={s.save}><Text style={s.saveText}>{saving ? 'Saving...' : 'Save Changes'}</Text></Pressable></View>}
        {securityOpen && <View style={s.security}><PasswordInput label="Current Password" value={currentPassword} onChangeText={setCurrentPassword} /><PasswordInput label="New Password" value={newPassword} onChangeText={setNewPassword} /><PasswordInput label="Confirm New Password" value={confirmPassword} onChangeText={setConfirmPassword} /><Pressable disabled={saving} onPress={updatePassword} style={s.save}><Text style={s.saveText}>{saving ? 'Updating...' : 'Update Password'}</Text></Pressable></View>}
        <Pressable onPress={logout} style={s.logout}><Ionicons name="log-out-outline" size={16} color="#FF4761" /><Text style={s.logoutText}>Log Out</Text></Pressable>
      </View>
      <View style={s.privacy}><View style={s.lock}><Ionicons name="lock-closed" size={16} color="#0759D9" /></View><View><Text style={s.privacyTitle}>Your information is safe with us.</Text><Text style={s.privacyText}>We protect your personal data and keep it confidential.</Text></View></View>
    </Animated.ScrollView>
  </SafeAreaView>;
}

function EditRow({ icon, label, value, onChangeText, keyboardType }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string; onChangeText: (value: string) => void; keyboardType: 'phone-pad' | 'email-address' }) { return <View style={s.editRow}><View style={s.editLabel}><Ionicons name={icon} size={14} color="#0759D9" /><Text style={s.rowLabel}>{label}</Text></View><TextInput style={s.editInput} value={value} onChangeText={onChangeText} keyboardType={keyboardType} autoCapitalize="none" /></View>; }
function PasswordInput({ label, value, onChangeText }: { label: string; value: string; onChangeText: (value: string) => void }) { return <View style={s.passwordField}><Text style={s.passwordLabel}>{label}</Text><TextInput style={s.passwordInput} value={value} onChangeText={onChangeText} secureTextEntry placeholder="Enter password" /></View>; }
function MenuRow({ icon, title, subtitle, onPress }: { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle: string; onPress: () => void }) { return <Pressable onPress={onPress} style={s.menuRow}><View style={s.menuIconSmall}><Ionicons name={icon} size={18} color="#0759D9" /></View><View style={s.menuCopy}><Text style={s.menuTitle}>{title}</Text><Text style={s.menuSubtitle}>{subtitle}</Text></View><Ionicons name="chevron-forward" size={18} color="#0759D9" /></Pressable>; }

const s = StyleSheet.create({ safe: { backgroundColor: '#07419C', flex: 1 }, content: { backgroundColor: '#FFFFFF', flexGrow: 1, paddingBottom: 14 }, loading: { alignItems: 'center', backgroundColor: '#F6F8FD', flex: 1, justifyContent: 'center' }, hero: { alignItems: 'center', backgroundColor: '#07419C', minHeight: 150, paddingTop: 42 }, back: { backgroundColor: '#073B96', left: 16, padding: 7, position: 'absolute', top: 17 }, heading: { color: '#FFF', fontSize: 23, fontWeight: '800' }, subheading: { borderBottomColor: '#D7E5FF', borderBottomWidth: StyleSheet.hairlineWidth, color: '#FFF', fontSize: 10, marginTop: 7, paddingBottom: 2 }, body: { alignItems: 'stretch', backgroundColor: '#FFFFFF', borderTopLeftRadius: 18, borderTopRightRadius: 18, marginTop: -18, paddingBottom: 18, paddingHorizontal: 8, paddingTop: 0 }, profileCard: { alignItems: 'center', backgroundColor: '#EAF4FF', borderColor: '#CFE2FA', borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 86, paddingHorizontal: 16 }, profileCopy: { flex: 1, marginLeft: 14 }, avatarOuter: { backgroundColor: '#FFFFFF', borderColor: '#FFFFFF', borderRadius: 35, borderWidth: 2, height: 70, padding: 3, width: 70 }, avatar: { alignItems: 'center', backgroundColor: '#E6F0FF', borderRadius: 31, height: 60, justifyContent: 'center', overflow: 'hidden', width: 60 }, camera: { alignItems: 'center', backgroundColor: '#0759D9', borderColor: '#FFF', borderRadius: 9, borderWidth: 1, bottom: 0, height: 18, justifyContent: 'center', position: 'absolute', right: -1, width: 18 }, name: { color: '#10295E', fontSize: 13, fontWeight: '800' }, role: { alignSelf: 'flex-start', backgroundColor: '#D3E8FF', borderRadius: 7, color: '#0759D9', fontSize: 7, marginTop: 3, overflow: 'hidden', paddingHorizontal: 7, paddingVertical: 2 }, member: { alignItems: 'center', flexDirection: 'row', gap: 5, marginTop: 7 }, memberText: { color: '#667FA8', fontSize: 7 }, menuPanel: { backgroundColor: '#FFFFFF', borderColor: '#E8EDF5', borderRadius: 11, borderWidth: StyleSheet.hairlineWidth, marginTop: 12, overflow: 'hidden', paddingHorizontal: 9 }, infoCard: { backgroundColor: '#FFFFFF', borderColor: '#E7EBF3', borderRadius: 10, borderWidth: 1, marginTop: 8, paddingHorizontal: 9 }, row: { alignItems: 'center', borderBottomColor: '#EDF0F5', borderBottomWidth: 1, flexDirection: 'row', minHeight: 36 }, rowLabel: { color: '#26385D', fontSize: 8, fontWeight: '700', marginLeft: 7, width: 105 }, rowValue: { color: '#152654', flex: 1, fontSize: 8 }, editRow: { borderBottomColor: '#EDF0F5', borderBottomWidth: 1, paddingVertical: 7 }, editLabel: { alignItems: 'center', flexDirection: 'row', marginBottom: 5 }, editInput: { backgroundColor: '#F7F9FD', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#152654', fontSize: 9, height: 36, paddingHorizontal: 9 }, save: { alignItems: 'center', backgroundColor: '#0646A8', borderRadius: 7, marginVertical: 9, paddingVertical: 10 }, saveText: { color: '#FFF', fontSize: 9, fontWeight: '800' }, menuCopy: { flex: 1 }, menuTitle: { color: '#10295E', fontSize: 9, fontWeight: '800' }, menuSubtitle: { color: '#718098', fontSize: 7, marginTop: 2 }, security: { backgroundColor: '#F7F9FD', borderRadius: 9, marginTop: 8, padding: 10 }, passwordField: { marginBottom: 8 }, passwordLabel: { color: '#26385D', fontSize: 8, fontWeight: '700', marginBottom: 5 }, passwordInput: { backgroundColor: '#FFF', borderColor: '#DCE4F1', borderRadius: 6, borderWidth: 1, color: '#152654', fontSize: 9, height: 38, paddingHorizontal: 10 }, menuRow: { alignItems: 'center', borderBottomColor: '#E8ECF3', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 53, paddingHorizontal: 3 }, menuIconSmall: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 16, height: 32, justifyContent: 'center', marginRight: 10, width: 32 }, logout: { alignItems: 'center', backgroundColor: '#FFF3F6', borderRadius: 18, flexDirection: 'row', gap: 8, justifyContent: 'center', marginHorizontal: 10, marginTop: 13, minHeight: 38 }, logoutText: { color: '#FF4761', fontSize: 10, fontWeight: '700' }, privacy: { alignItems: 'center', backgroundColor: '#EAF2FF', borderRadius: 9, flexDirection: 'row', marginHorizontal: 8, marginTop: 'auto', padding: 10 }, lock: { alignItems: 'center', backgroundColor: '#D7E8FF', borderRadius: 16, height: 30, justifyContent: 'center', marginRight: 9, width: 30 }, privacyTitle: { color: '#0759D9', fontSize: 8, fontWeight: '800' }, privacyText: { color: '#718098', fontSize: 6.5, marginTop: 2 } });
