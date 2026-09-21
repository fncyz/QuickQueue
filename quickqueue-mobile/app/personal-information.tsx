import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/services/api';

type Profile = { username: string; first_name: string; middle_name: string; last_name: string; suffix: string; birthdate: string; sex_display: string; email: string | null; contact_number: string; province: string; municipality: string; barangay: string; age: number; created_at: string };

export default function PersonalInformationScreen() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [token, setToken] = useState('');
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState('');
  const [contact, setContact] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const accessToken = await AsyncStorage.getItem('quickqueue.accessToken');
        if (!accessToken) return router.replace('/login');
        setToken(accessToken);
        const response = await api.get<Profile>('profile/', { headers: { Authorization: `Bearer ${accessToken}` } });
        setProfile(response.data); setEmail(response.data.email || ''); setContact(response.data.contact_number);
      } catch (error: any) { Alert.alert('Unable to load profile', error?.response?.data?.message || 'Please check your connection.'); }
    };
    load();
  }, []);

  const save = async () => {
    if (!contact.trim()) return Alert.alert('Contact number required', 'Enter your contact number.');
    try {
      setSaving(true);
      const response = await api.patch<Profile>('profile/', { email, contact_number: contact }, { headers: { Authorization: `Bearer ${token}` } });
      setProfile(response.data); setEditing(false); Alert.alert('Profile updated', 'Your contact information has been saved.');
    } catch (error: any) { Alert.alert('Profile not updated', error?.response?.data?.message || 'Please try again.'); }
    finally { setSaving(false); }
  };

  if (!profile) return <SafeAreaView style={s.loading}><ActivityIndicator color="#FFFFFF" /></SafeAreaView>;
  const middleInitial = profile.middle_name ? ` ${profile.middle_name.charAt(0).toUpperCase()}.` : '';
  const fullName = `${profile.first_name}${middleInitial} ${profile.last_name}${profile.suffix ? ` ${profile.suffix}` : ''}`;
  const memberSince = new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  const birthdate = new Date(`${profile.birthdate}T00:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return <SafeAreaView style={s.safe} edges={['top']}><ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
    <View style={s.hero}><Pressable onPress={() => router.back()} style={s.back}><Ionicons name="chevron-back" size={27} color="#FFFFFF" /></Pressable><Text style={s.heading}>My Profile</Text><Text style={s.subheading}>View and manage your personal information.</Text></View>
    <View style={s.sheet}>
      <View style={s.avatarOuter}><View style={s.avatar}><Ionicons name="person" size={66} color="#668ED9" /></View><View style={s.camera}><Ionicons name="camera" size={12} color="#FFFFFF" /></View></View>
      <Text style={s.name}>{fullName}</Text><Text style={s.role}>Resident</Text><View style={s.member}><Ionicons name="calendar-outline" size={11} color="#7183A1" /><Text style={s.memberText}>Member since {memberSince}</Text></View>
      <Pressable onPress={() => setEditing((value) => !value)} style={s.edit}><Ionicons name="create-outline" size={12} color="#0873FF" /><Text style={s.editText}>{editing ? 'Cancel Editing' : 'Edit Profile'}</Text></Pressable>
      <View style={s.sectionTitle}><View style={s.sectionIcon}><Ionicons name="person-outline" size={15} color="#0873FF" /></View><Text style={s.sectionText}>Personal Information</Text></View>
      <View style={s.card}>
        <Info icon="person-outline" label="Username" value={`@${profile.username}`} /><Info icon="calendar-outline" label="Age" value={String(profile.age)} /><Info icon="male-female-outline" label="Sex" value={profile.sex_display} /><Info icon="calendar-outline" label="Birthdate" value={birthdate} /><Info icon="location-outline" label="Barangay" value={profile.barangay} /><Info icon="business-outline" label="Municipality" value={profile.municipality} /><Info icon="map-outline" label="Province" value={profile.province} />
        {editing ? <><Edit icon="call-outline" label="Contact Number" value={contact} onChange={setContact} keyboardType="phone-pad" /><Edit icon="mail-outline" label="Email Address" value={email} onChange={setEmail} keyboardType="email-address" /><Pressable disabled={saving} onPress={save} style={s.save}><Text style={s.saveText}>{saving ? 'Saving...' : 'Save Changes'}</Text></Pressable></> : <><Info icon="call-outline" label="Contact Number" value={profile.contact_number} /><Info icon="mail-outline" label="Email Address" value={profile.email || 'Not provided'} /></>}
      </View>
      <Pressable onPress={() => router.back()} style={s.security}><View style={s.securityIcon}><Ionicons name="shield-checkmark-outline" size={19} color="#0873FF" /></View><View style={s.securityCopy}><Text style={s.securityTitle}>Account Security</Text><Text style={s.securityText}>Manage your password and keep your account secure.</Text></View><Ionicons name="chevron-forward" size={18} color="#0873FF" /></Pressable>
    </View>
  </ScrollView></SafeAreaView>;
}

function Info({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) { return <View style={s.row}><View style={s.rowIcon}><Ionicons name={icon} size={12} color="#0873FF" /></View><Text style={s.label}>{label}</Text><Text style={s.value}>{value}</Text></View>; }
function Edit({ icon, label, value, onChange, keyboardType }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string; onChange: (value: string) => void; keyboardType: 'phone-pad' | 'email-address' }) { return <View style={s.editRow}><View style={s.editLabel}><View style={s.rowIcon}><Ionicons name={icon} size={12} color="#0873FF" /></View><Text style={s.label}>{label}</Text></View><TextInput value={value} onChangeText={onChange} keyboardType={keyboardType} autoCapitalize="none" style={s.input} /></View>; }

const s = StyleSheet.create({
  safe: { backgroundColor: '#0744AD', flex: 1 }, loading: { alignItems: 'center', backgroundColor: '#0744AD', flex: 1, justifyContent: 'center' }, content: { backgroundColor: '#FFFFFF', flexGrow: 1 }, hero: { alignItems: 'center', backgroundColor: '#0744AD', minHeight: 170, paddingTop: 25 }, back: { backgroundColor: '#073B98', left: 14, padding: 7, position: 'absolute', top: 6 }, heading: { color: '#FFFFFF', fontSize: 21, fontWeight: '800' }, subheading: { color: '#FFFFFF', fontSize: 10, marginTop: 6 }, sheet: { alignItems: 'stretch', backgroundColor: '#FFFFFF', borderTopLeftRadius: 24, borderTopRightRadius: 24, marginTop: -24, paddingBottom: 20, paddingHorizontal: 15, paddingTop: 70 }, avatarOuter: { alignSelf: 'center', backgroundColor: '#FFFFFF', borderColor: '#E3ECF9', borderRadius: 51, borderWidth: 3, height: 102, padding: 6, position: 'absolute', top: -48, width: 102 }, avatar: { alignItems: 'center', backgroundColor: '#EAF2FF', borderRadius: 43, height: 84, justifyContent: 'center', overflow: 'hidden', width: 84 }, camera: { alignItems: 'center', backgroundColor: '#0754C7', borderColor: '#FFFFFF', borderRadius: 12, borderWidth: 2, bottom: 1, height: 24, justifyContent: 'center', position: 'absolute', right: -2, width: 24 }, name: { color: '#0A2D71', fontSize: 15, fontWeight: '800', textAlign: 'center' }, role: { alignSelf: 'center', backgroundColor: '#DCEEFF', borderRadius: 8, color: '#0873FF', fontSize: 7, marginTop: 4, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3 }, member: { alignItems: 'center', flexDirection: 'row', gap: 5, justifyContent: 'center', marginTop: 9 }, memberText: { color: '#7183A1', fontSize: 7 }, edit: { alignItems: 'center', backgroundColor: '#F0F5FF', borderRadius: 9, flexDirection: 'row', gap: 6, justifyContent: 'center', marginHorizontal: 19, marginTop: 10, minHeight: 29 }, editText: { color: '#0873FF', fontSize: 8, fontWeight: '700' }, sectionTitle: { alignItems: 'center', flexDirection: 'row', gap: 7, marginBottom: 8, marginTop: 10 }, sectionIcon: { alignItems: 'center', backgroundColor: '#ECF4FF', borderRadius: 14, height: 28, justifyContent: 'center', width: 28 }, sectionText: { color: '#102F6B', fontSize: 10, fontWeight: '800' }, card: { borderColor: '#E4EAF3', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, paddingHorizontal: 10 }, row: { alignItems: 'center', borderBottomColor: '#E9EEF5', borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row', minHeight: 35 }, rowIcon: { alignItems: 'center', backgroundColor: '#EFF5FF', borderRadius: 10, height: 21, justifyContent: 'center', width: 21 }, label: { color: '#17356F', fontSize: 7.5, fontWeight: '800', marginLeft: 8, width: 145 }, value: { color: '#1F396A', flex: 1, fontSize: 7.5 }, editRow: { borderBottomColor: '#E9EEF5', borderBottomWidth: StyleSheet.hairlineWidth, paddingVertical: 7 }, editLabel: { alignItems: 'center', flexDirection: 'row', marginBottom: 5 }, input: { backgroundColor: '#F8FAFE', borderColor: '#DCE5F2', borderRadius: 7, borderWidth: StyleSheet.hairlineWidth, color: '#1F396A', fontSize: 9, height: 36, paddingHorizontal: 10 }, save: { alignItems: 'center', backgroundColor: '#0754C7', borderRadius: 8, marginVertical: 9, paddingVertical: 10 }, saveText: { color: '#FFFFFF', fontSize: 9, fontWeight: '800' }, security: { alignItems: 'center', borderColor: '#E4EAF3', borderRadius: 10, borderWidth: StyleSheet.hairlineWidth, flexDirection: 'row', marginTop: 9, minHeight: 55, padding: 9 }, securityIcon: { alignItems: 'center', backgroundColor: '#EDF4FF', borderRadius: 16, height: 33, justifyContent: 'center', width: 33 }, securityCopy: { flex: 1, marginLeft: 9 }, securityTitle: { color: '#12336F', fontSize: 9, fontWeight: '800' }, securityText: { color: '#7183A1', fontSize: 6.5, marginTop: 3 },
});
