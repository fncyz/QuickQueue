import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '@/components/Typography';
import { SafeAreaView } from 'react-native-safe-area-context';

export function StaticTabScreen({ title, message, icon }: { title: string; message: string; icon: keyof typeof Ionicons.glyphMap }) {
  return <SafeAreaView style={styles.page}><View style={styles.card}><Ionicons name={icon} size={44} color="#0759D9" /><Text style={styles.title}>{title}</Text><Text style={styles.message}>{message}</Text></View></SafeAreaView>;
}
const styles = StyleSheet.create({ page: { alignItems: 'center', backgroundColor: '#F8FAFF', flex: 1, justifyContent: 'center', padding: 24 }, card: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 18, padding: 28, width: '100%' }, title: { color: '#0346A8', fontSize: 21, fontWeight: '800', marginTop: 13 }, message: { color: '#687189', fontSize: 14, lineHeight: 20, marginTop: 8, textAlign: 'center' } });
