import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, ImageBackground, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Text } from '@/components/Typography';
import { readRecentResidentProfile, type RecentResidentProfile } from '@/services/offline-cache';

const background = require('../../assets/images/login.png');
const logo = require('../../assets/images/logo.png');

export default function WelcomeBackScreen() {
  const [profile, setProfile] = useState<RecentResidentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([AsyncStorage.getItem('quickqueue.accessToken'), readRecentResidentProfile()])
      .then(([token, savedProfile]) => {
        if (token) return router.replace('/(tabs)');
        if (!savedProfile) return router.replace('/login');
        setProfile(savedProfile);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading || !profile) return <SafeAreaView style={s.loading}><ActivityIndicator color="#FFC21C" /></SafeAreaView>;

  return <View style={s.screen}>
    <ImageBackground source={background} resizeMode="cover" style={StyleSheet.absoluteFill} />
    <SafeAreaView style={s.safe} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
        <View style={s.branding}>
          <Image source={logo} resizeMode="contain" style={s.logo} accessibilityLabel="QuickQueue logo" />
          <Text style={s.title}>WELCOME BACK</Text>
          <Text style={s.subtitle}>Good to see you again</Text>
        </View>

        <View style={s.actions}>
          <Pressable accessibilityRole="button" onPress={() => router.push({ pathname: '/login', params: { displayName: profile.displayName, from: 'saved-profile', username: profile.username } })} style={s.profileCard}>
            <Text numberOfLines={1} style={s.profileName}>{profile.displayName}</Text>
            <View style={s.chevron}><Ionicons name="chevron-forward" size={20} color="#0759D9" /></View>
          </Pressable>

          <View style={s.dividerRow}><View style={s.divider} /><Text style={s.dividerText}>Or sign in with</Text><View style={s.divider} /></View>

          <Pressable accessibilityRole="button" onPress={() => router.push({ pathname: '/login', params: { from: 'welcome-back' } })} style={s.otherButton}><Text style={s.otherText}>Use another profile</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={() => router.push({ pathname: '/register', params: { from: 'welcome-back' } })} style={s.createButton}><Text style={s.createText}>Create new account</Text></Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  </View>;
}

const s = StyleSheet.create({
  screen: { backgroundColor: '#063C99', flex: 1 },
  safe: { flex: 1 },
  loading: { alignItems: 'center', backgroundColor: '#063C99', flex: 1, justifyContent: 'center' },
  content: { alignItems: 'center', flexGrow: 1, paddingBottom: 32, paddingHorizontal: 24 },
  branding: { alignItems: 'center', height: 250, paddingTop: 32 },
  logo: { height: 94, width: 94 },
  title: { color: '#082E78', fontSize: 25, fontWeight: '800', letterSpacing: 0.2, marginTop: 5 },
  subtitle: { color: '#5B6475', fontSize: 13, marginTop: 1 },
  actions: { marginTop: 20, maxWidth: 500, width: '100%' },
  profileCard: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 8, borderWidth: 0, elevation: 3, flexDirection: 'row', height: 59, overflow: 'hidden', paddingLeft: 18, shadowColor: '#31598A', shadowOffset: { height: 3, width: 0 }, shadowOpacity: 0.14, shadowRadius: 7 },
  profileName: { color: '#12366F', flex: 1, fontSize: 14, fontWeight: '800' },
  chevron: { alignItems: 'center', alignSelf: 'stretch', backgroundColor: '#FFFFFF', justifyContent: 'center', width: 42 },
  dividerRow: { alignItems: 'center', flexDirection: 'row', gap: 12, marginVertical: 31 },
  divider: { backgroundColor: 'rgba(255,255,255,0.65)', flex: 1, height: 1 },
  dividerText: { color: '#FFFFFF', fontSize: 11 },
  otherButton: { alignItems: 'center', backgroundColor: '#FFC21C', borderRadius: 9, elevation: 3, height: 48, justifyContent: 'center', shadowColor: '#001D57', shadowOffset: { height: 3, width: 0 }, shadowOpacity: 0.2, shadowRadius: 4 },
  otherText: { color: '#102342', fontSize: 12, fontWeight: '800' },
  createButton: { alignItems: 'center', backgroundColor: '#F1F6FF', borderRadius: 9, elevation: 3, height: 48, justifyContent: 'center', marginTop: 22, shadowColor: '#001D57', shadowOffset: { height: 3, width: 0 }, shadowOpacity: 0.2, shadowRadius: 4 },
  createText: { color: '#12366F', fontSize: 12, fontWeight: '700' },
});
