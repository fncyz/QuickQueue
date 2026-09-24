import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Animated, Image, Pressable, StyleSheet, View } from 'react-native';
import { Text, TextInput } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';
import { useAppTheme } from '@/contexts/app-theme';
import { useCoverHeaderScroll } from '@/hooks/use-cover-header-scroll';

type Profile = { username: string; first_name: string; middle_name: string; last_name: string; suffix: string; birthdate: string; sex_display: string; email: string | null; contact_number: string; province: string; municipality: string; barangay: string; age: number; created_at: string };

export default function PersonalInformationScreen() {
  const { colors } = useAppTheme();
  const coverHeader = useCoverHeaderScroll();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [token, setToken] = useState('');
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState('');
  const [contact, setContact] = useState('');
  const [saving, setSaving] = useState(false);
  const [photo, setPhoto] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return router.replace('/login');
        setToken(accessToken);
        const response = await api.get<Profile>('profile/', { headers: { Authorization: `Bearer ${accessToken}` } });
        const savedPhoto = await AsyncStorage.getItem(`quickqueue.profilePhoto.${response.data.username}`);
        setProfile(response.data); setEmail(response.data.email || ''); setContact(response.data.contact_number); setPhoto(savedPhoto);
      } catch (error: any) { Alert.alert('Unable to load profile', error?.response?.data?.message || 'Please check your connection.'); }
    };
    load();
  }, []);

  const save = async () => {
    if (!contact.trim()) return Alert.alert('Contact number required', 'Enter your contact number.');
    try {
      setSaving(true);
      const response = await api.patch<Profile>('profile/', { email, contact_number: contact }, { headers: { Authorization: `Bearer ${token}` } });
      if (photo) await AsyncStorage.setItem(`quickqueue.profilePhoto.${response.data.username}`, photo);
      setProfile(response.data); setEditing(false); Alert.alert('Profile updated', 'Your contact information has been saved.');
    } catch (error: any) { Alert.alert('Profile not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  const pickPhoto = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return Alert.alert('Permission required', 'Allow photo access to choose a profile picture.');
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsEditing: true, aspect: [1, 1], quality: 0.8 });
    if (result.canceled || !result.assets[0]) return;
    const selected = result.assets[0];
    if (selected.fileSize && selected.fileSize >= 5 * 1024 * 1024) {
      Alert.alert('Image is too large', 'Please select a profile picture smaller than 5 MB.');
      return;
    }
    setPhoto(selected.uri);
    setEditing(true);
  };

  if (!profile) return <SafeAreaView style={[s.loading, { backgroundColor: colors.background }]}><ActivityIndicator color={colors.accent} /></SafeAreaView>;
  const middleInitial = profile.middle_name ? ` ${profile.middle_name.charAt(0).toUpperCase()}.` : '';
  const fullName = `${profile.first_name}${middleInitial} ${profile.last_name}${profile.suffix ? ` ${profile.suffix}` : ''}`;
  const memberSince = new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  const birthdate = new Date(`${profile.birthdate}T00:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return <SafeAreaView style={[s.safe, { backgroundColor: colors.background }]} edges={['top']}><Animated.ScrollView contentContainerStyle={[s.content, { backgroundColor: colors.background }]} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} onScroll={coverHeader.onScroll} scrollEventThrottle={16}>
    <Animated.View style={[s.hero, { backgroundColor: colors.primary }, coverHeader.headerStyle]}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFFFFF" /></Pressable><Text style={s.heading}>Edit Personal Information</Text><Text style={s.subheading}>Update your details and profile picture.</Text></Animated.View>
    <View style={[s.sheet, { backgroundColor: colors.background }]}>
      <Pressable accessibilityLabel="Upload profile picture" onPress={pickPhoto} style={s.avatarOuter}><View style={s.avatar}>{photo ? <Image source={{ uri: photo }} style={s.photo} /> : <Ionicons name="person" size={66} color="#668ED9" />}</View><View style={s.camera}><Ionicons name="camera" size={12} color="#FFFFFF" /></View></Pressable>
      <Text style={[s.name, { color: colors.text }]}>{fullName}</Text><Text style={s.role}>Resident</Text><View style={s.member}><Ionicons name="calendar-outline" size={11} color={colors.muted} /><Text style={[s.memberText, { color: colors.muted }]}>Member since {memberSince}</Text></View>
      <Pressable onPress={() => setEditing((value) => !value)} style={s.edit}><Ionicons name="create-outline" size={12} color="#0873FF" /><Text style={s.editText}>{editing ? 'Cancel Editing' : 'Edit Profile'}</Text></Pressable>
      <View style={s.sectionTitle}><View style={s.sectionIcon}><Ionicons name="person-outline" size={15} color="#0873FF" /></View><Text style={s.sectionText}>Personal Information</Text></View>
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Info icon="person-outline" label="Username" value={`@${profile.username}`} /><Info icon="calendar-outline" label="Age" value={String(profile.age)} /><Info icon="male-female-outline" label="Sex" value={profile.sex_display} /><Info icon="calendar-outline" label="Birthdate" value={birthdate} /><Info icon="location-outline" label="Barangay" value={profile.barangay} /><Info icon="business-outline" label="Municipality" value={profile.municipality} /><Info icon="map-outline" label="Province" value={profile.province} />
        {editing ? <><Pressable onPress={pickPhoto} style={s.upload}><Ionicons name="image-outline" size={16} color="#0873FF" /><Text style={s.uploadText}>{photo ? 'Change Profile Picture' : 'Upload Profile Picture'}</Text><Text style={s.uploadLimit}>Max 5 MB</Text></Pressable>{photo && <Image source={{ uri: photo }} style={s.preview} />}<Edit icon="call-outline" label="Contact Number" value={contact} onChange={setContact} keyboardType="phone-pad" /><Edit icon="mail-outline" label="Email Address" value={email} onChange={setEmail} keyboardType="email-address" /><Pressable disabled={saving} onPress={save} style={s.save}><Text style={s.saveText}>{saving ? 'Saving...' : 'Save Changes'}</Text></Pressable></> : <><Info icon="call-outline" label="Contact Number" value={profile.contact_number} /><Info icon="mail-outline" label="Email Address" value={profile.email || 'Not provided'} /></>}
      </View>
    </View>
  </Animated.ScrollView></SafeAreaView>;
}

function Info({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) { const { colors } = useAppTheme(); return <View style={[s.row, { borderBottomColor: colors.border }]}><View style={[s.rowIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={icon} size={12} color={colors.accent} /></View><Text style={[s.label, { color: colors.text }]}>{label}</Text><Text style={[s.value, { color: colors.muted }]}>{value}</Text></View>; }
function Edit({ icon, label, value, onChange, keyboardType }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string; onChange: (value: string) => void; keyboardType: 'phone-pad' | 'email-address' }) { const { colors } = useAppTheme(); return <View style={[s.editRow, { borderBottomColor: colors.border }]}><View style={s.editLabel}><View style={[s.rowIcon, { backgroundColor: colors.iconBackground }]}><Ionicons name={icon} size={12} color={colors.accent} /></View><Text style={[s.label, { color: colors.text }]}>{label}</Text></View><TextInput value={value} onChangeText={onChange} keyboardType={keyboardType} autoCapitalize="none" placeholderTextColor={colors.muted} style={[s.input, { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text }]} /></View>; }

const s = StyleSheet.create({
  safe: { backgroundColor: '#0744AD', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#0744AD', flex: 1, justifyContent: 'center' }, content: { backgroundColor: '#FFFFFF', flexGrow: 1 }, hero: { alignItems: 'center', backgroundColor: '#0744AD', minHeight: 170, paddingTop: 25 }, back: { backgroundColor: '#073B98', left: 14, padding: 7, position: 'absolute', top: 6 }, heading: { color: '#FFFFFF', fontSize: 21, fontWeight: '800' }, subheading: { color: '#FFFFFF', fontSize: 11, marginTop: 6 }, sheet: { alignItems: 'stretch', backgroundColor: '#FFFFFF', borderTopLeftRadius: 24, borderTopRightRadius: 24, marginTop: -24, paddingBottom: 20, paddingHorizontal: 15, paddingTop: 70 }, avatarOuter: { alignSelf: 'center', backgroundColor: '#FFFFFF', borderColor: '#E3ECF9', borderRadius: 51, borderWidth: 3, height: 102, padding: 6, position: 'absolute', top: -48, width: 102 }, avatar: { alignItems: 'center', backgroundColor: '#EAF2FF', borderRadius: 43, height: 84, justifyContent: 'center', overflow: 'hidden', width: 84 }, photo: { height: '100%', width: '100%' }, camera: { alignItems: 'center', backgroundColor: '#0754C7', borderColor: '#FFFFFF', borderRadius: 12, borderWidth: 2, bottom: 1, height: 24, justifyContent: 'center', position: 'absolute', right: -2, width: 24 }, name: { color: '#0A2D71', fontSize: 17, fontWeight: '800', textAlign: 'center' }, role: { alignSelf: 'center', backgroundColor: '#DCEEFF', borderRadius: 8, color: '#0873FF', fontSize: 9, marginTop: 4, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3 }, member: { alignItems: 'center', flexDirection: 'row', gap: 5, justifyContent: 'center', marginTop: 9 }, memberText: { color: '#7183A1', fontSize: 9 }, edit: { alignItems: 'center', backgroundColor: '#F0F5FF', borderRadius: 9, flexDirection: 'row', gap: 6, justifyContent: 'center', marginHorizontal: 19, marginTop: 10, minHeight: 34 }, editText: { color: '#0873FF', fontSize: 10, fontWeight: '700' }, sectionTitle: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 8, marginTop: 12 }, sectionIcon: { alignItems: 'center', backgroundColor: '#ECF4FF', borderRadius: 14, height: 28, justifyContent: 'center', width: 28 }, sectionText: { color: '#102F6B', fontSize: 13, fontWeight: '800' }, card: { borderColor: '#E4EAF3', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, paddingHorizontal: 10 }, upload: { alignItems: 'center', borderBottomColor: '#E9EEF5', borderBottomWidth: 1, flexDirection: 'row', gap: 7, minHeight: 46 }, uploadText: { color: '#0873FF', flex: 1, fontSize: 11, fontWeight: '800' }, uploadLimit: { color: '#7183A1', fontSize: 9 }, preview: { alignSelf: 'center', borderRadius: 34, height: 68, marginVertical: 10, width: 68 }, row: { alignItems: 'center', borderBottomColor: '#E9EEF5', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 43 }, rowIcon: { alignItems: 'center', backgroundColor: '#EFF5FF', borderRadius: 11, height: 23, justifyContent: 'center', width: 23 }, label: { color: '#17356F', fontSize: 11, fontWeight: '800', marginLeft: 8, width: 125 }, value: { color: '#1F396A', flex: 1, fontSize: 11 }, editRow: { borderBottomColor: '#E9EEF5', borderBottomWidth: StyleSheet.hairlineWidth, paddingVertical: 8 }, editLabel: { alignItems: 'center', flexDirection: 'row', marginBottom: 6 }, input: { backgroundColor: '#F8FAFE', borderColor: '#DCE5F2', borderRadius: 7, borderWidth: StyleSheet.hairlineWidth, color: '#1F396A', fontSize: 11, height: 38, paddingHorizontal: 10 }, save: { alignItems: 'center', backgroundColor: '#0754C7', borderRadius: 8, marginVertical: 9, paddingVertical: 11 }, saveText: { color: '#FFFFFF', fontSize: 11, fontWeight: '800' }, security: { alignItems: 'center', borderColor: '#E4EAF3', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', marginTop: 9, minHeight: 55, padding: 9 }, securityIcon: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 16, height: 33, justifyContent: 'center', width: 33 }, securityCopy: { flex: 1, marginLeft: 9 }, securityTitle: { color: '#12336F', fontSize: 11, fontWeight: '800' }, securityText: { color: '#7183A1', fontSize: 9, marginTop: 3 },
});
