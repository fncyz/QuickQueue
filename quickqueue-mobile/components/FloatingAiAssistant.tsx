import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef, useState } from 'react';
import { Image, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Text, TextInput } from '@/components/Typography';
import { useAppTheme } from '@/contexts/app-theme';
import { useConnectivity } from '@/contexts/connectivity';

const assistantLogo = require('../assets/images/qq-ai.png');
const assistantBlue = '#0759D9';
const suggestions = ['Requirements for Clearance', 'Service Fees', 'Office Hours', 'Book an Appointment', 'Queue Status'] as const;
const answers: Record<(typeof suggestions)[number], string> = {
  'Requirements for Clearance': 'For a Barangay Clearance, prepare one valid government-issued ID. Additional requirements may vary by barangay, so confirm the details shown when you book.',
  'Service Fees': 'Service fees depend on the document and your barangay. You can review the exact fee before confirming an appointment in QuickQueue.',
  'Office Hours': 'The barangay office is open Monday–Friday, 8:00 AM–5:00 PM, and Saturday, 8:00 AM–12:00 PM. It is closed on Sundays and holidays.',
  'Book an Appointment': 'To book, open the Book tab, select a barangay service, choose an available date and time, then review and confirm your appointment.',
  'Queue Status': 'You can see your live queue number and estimated waiting time in the Queue tab. Pull down there to refresh the latest status.',
};
type Message = { id: string; role: 'assistant' | 'resident'; text: string; time: string };
const timeNow = () => new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date());

function suggestionsFor(message: string): readonly (typeof suggestions)[number][] {
  const normalized = message.toLowerCase();
  if (normalized.includes('valid government-issued id')) return ['Service Fees', 'Book an Appointment', 'Office Hours'];
  if (normalized.includes('exact fee')) return ['Requirements for Clearance', 'Book an Appointment', 'Office Hours'];
  if (normalized.includes('monday') || normalized.includes('saturday')) return ['Book an Appointment', 'Queue Status', 'Requirements for Clearance'];
  if (normalized.includes('select a barangay service')) return ['Requirements for Clearance', 'Service Fees', 'Office Hours'];
  if (normalized.includes('live queue number')) return ['Book an Appointment', 'Office Hours', 'Service Fees'];
  return suggestions;
}

function responseFor(input: string) {
  const normalized = input.toLowerCase();
  const matchingSuggestion = suggestions.find((suggestion) => normalized.includes(suggestion.toLowerCase()));
  if (matchingSuggestion) return answers[matchingSuggestion];
  if (normalized.includes('clearance') || normalized.includes('requirement')) return answers['Requirements for Clearance'];
  if (normalized.includes('fee') || normalized.includes('cost') || normalized.includes('price')) return answers['Service Fees'];
  if (normalized.includes('hour') || normalized.includes('open') || normalized.includes('close')) return answers['Office Hours'];
  if (normalized.includes('book') || normalized.includes('appointment')) return answers['Book an Appointment'];
  if (normalized.includes('queue') || normalized.includes('wait') || normalized.includes('status')) return answers['Queue Status'];
  return 'I can help with clearance requirements, service fees, office hours, appointments, and queue status. Choose a suggested question or ask me about one of those topics.';
}

export function FloatingAiAssistant() {
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const { colors, isDark } = useAppTheme();
  const { isOnline } = useConnectivity();
  const scrollRef = useRef<ScrollView>(null);
  const nextId = useRef(1);
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<Message[]>(() => [{ id: 'assistant-welcome', role: 'assistant', text: 'Hello! I’m the QuickQueue AI Assistant. How can I help you today?', time: timeNow() }]);
  const size = Math.max(56, Math.min(62, width * 0.15));
  const availableHeight = Math.max(280, height - insets.top - insets.bottom - 24);

  useEffect(() => {
    if (isOpen) requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
  }, [isOpen, messages]);

  const send = (text = draft) => {
    const trimmed = text.trim();
    if (!trimmed || !isOnline) return;
    const timestamp = timeNow();
    const residentId = `resident-${nextId.current++}`;
    const assistantId = `assistant-${nextId.current++}`;
    setMessages((current) => [...current,
      { id: residentId, role: 'resident', text: trimmed, time: timestamp },
      { id: assistantId, role: 'assistant', text: responseFor(trimmed), time: timestamp },
    ]);
    setDraft('');
  };

  if (!isOpen) return <Pressable accessibilityHint="Opens the QuickQueue Smart Assistant" accessibilityLabel="Open QuickQueue Smart Assistant" accessibilityRole="button" onPress={() => setIsOpen(true)} style={({ pressed }) => [styles.button, { bottom: insets.bottom + 101, height: size, opacity: pressed ? 0.82 : 1, right: Math.max(18, width * 0.045), transform: [{ scale: pressed ? 0.96 : 1 }], width: size }]}>
    <Image source={assistantLogo} resizeMode="contain" style={[styles.logo, { height: size - 8, width: size - 8 }]} />
  </Pressable>;

  const panel = isDark ? '#131E30' : '#FFFFFF';
  const assistantBubble = isDark ? '#1C2B42' : '#F0F5FC';
  const inputBackground = isDark ? '#19263A' : '#F8FAFD';
  return <Modal animationType="fade" onRequestClose={() => setIsOpen(false)} transparent visible>
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.modalRoot}>
      <View style={[styles.backdrop, { paddingBottom: insets.bottom + 12, paddingHorizontal: width < 380 ? 10 : 16, paddingTop: insets.top + 12 }]}>
        <View style={[styles.chatWindow, { backgroundColor: panel, borderColor: colors.border, height: Math.min(720, availableHeight) }]}>
          <View style={[styles.header, { backgroundColor: isDark ? '#102851' : '#EAF3FF', borderBottomColor: colors.border }]}>
            <Image accessibilityLabel="QuickQueue AI logo" source={assistantLogo} style={styles.headerLogo} />
            <View style={styles.headerCopy}><Text numberOfLines={1} style={[styles.headerName, { color: colors.text }]}>QuickQueue Smart Assistant</Text><View style={styles.statusRow}><View style={[styles.statusDot, { backgroundColor: isOnline ? '#20B573' : '#E05252' }]} /><Text style={[styles.statusText, { color: colors.muted }]}>{isOnline ? 'Online' : 'Offline'}</Text></View></View>
            <Pressable accessibilityLabel="Minimize assistant" hitSlop={10} onPress={() => setIsOpen(false)} style={({ pressed }) => [styles.closeButton, { backgroundColor: isDark ? '#203553' : '#FFFFFF', opacity: pressed ? 0.65 : 1 }]}><Ionicons color={colors.text} name="close" size={22} /></Pressable>
          </View>
          {!isOnline && <View accessibilityLiveRegion="polite" style={styles.offlineBanner}><Ionicons color="#9B3A32" name="cloud-offline-outline" size={18} /><Text style={styles.offlineText}>An internet connection is required to send messages. We’ll reconnect automatically.</Text></View>}
          <ScrollView contentContainerStyle={styles.conversation} keyboardShouldPersistTaps="handled" onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })} ref={scrollRef} showsVerticalScrollIndicator={false}>
            {messages.map((message, index) => <View key={message.id}>
              <MessageBubble assistantBubble={assistantBubble} colors={colors} message={message} />
              {message.role === 'assistant' && index === messages.length - 1 && <View onLayout={() => requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }))} style={[styles.suggestionsCard, { backgroundColor: inputBackground, borderColor: colors.border }]}><Text style={[styles.suggestionsTitle, { color: colors.text }]}>Suggested Questions</Text><View style={styles.suggestionList}>{suggestionsFor(message.text).map((suggestion) => <Pressable accessibilityRole="button" disabled={!isOnline} key={`${message.id}-${suggestion}`} onPress={() => send(suggestion)} style={({ pressed }) => [styles.suggestion, { backgroundColor: panel, borderColor: isOnline ? '#B8D3FA' : colors.border, opacity: !isOnline ? 0.45 : pressed ? 0.65 : 1 }]}><Text style={[styles.suggestionText, { color: isOnline ? colors.accent : colors.muted }]}>{suggestion}</Text></Pressable>)}</View></View>}
            </View>)}
          </ScrollView>
          <View style={[styles.composer, { backgroundColor: panel, borderTopColor: colors.border }]}>
            <TextInput accessibilityLabel="Message QuickQueue Smart Assistant" editable={isOnline} onChangeText={setDraft} onSubmitEditing={() => send()} placeholder={isOnline ? 'Type your message…' : 'Connect to the internet to chat'} placeholderTextColor={colors.muted} returnKeyType="send" style={[styles.input, { backgroundColor: inputBackground, borderColor: colors.border, color: colors.text }]} value={draft} />
            <Pressable accessibilityLabel="Send message" disabled={!isOnline || !draft.trim()} onPress={() => send()} style={({ pressed }) => [styles.sendButton, { opacity: !isOnline || !draft.trim() ? 0.4 : pressed ? 0.72 : 1 }]}><Ionicons color="#FFFFFF" name="send" size={20} /></Pressable>
          </View>
        </View>
      </View>
    </KeyboardAvoidingView>
  </Modal>;
}

function MessageBubble({ assistantBubble, colors, message }: { assistantBubble: string; colors: { muted: string; text: string }; message: Message }) {
  const resident = message.role === 'resident';
  return <View style={[styles.messageRow, resident && styles.residentRow]}>{!resident && <Image source={assistantLogo} style={styles.messageAvatar} />}<View style={styles.messageContent}><View style={[styles.messageBubble, resident ? styles.residentBubble : { backgroundColor: assistantBubble }]}><Text style={[styles.messageText, { color: resident ? '#FFFFFF' : colors.text }]}>{message.text}</Text></View><Text style={[styles.timestamp, { color: colors.muted }, resident && styles.residentTimestamp]}>{message.time}</Text></View></View>;
}

const styles = StyleSheet.create({
  button: { alignItems: 'center', backgroundColor: assistantBlue, borderColor: '#76ACFA', borderRadius: 999, borderWidth: 2, elevation: 7, justifyContent: 'center', overflow: 'hidden', position: 'absolute', shadowColor: '#082F76', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.22, shadowRadius: 7, zIndex: 20 },
  logo: { borderRadius: 999 }, modalRoot: { flex: 1 },
  backdrop: { alignItems: 'center', backgroundColor: 'rgba(3, 15, 35, 0.42)', flex: 1, justifyContent: 'flex-end' },
  chatWindow: { borderRadius: 24, borderWidth: 1, elevation: 18, maxWidth: 520, overflow: 'hidden', shadowColor: '#001A45', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.28, shadowRadius: 20, width: '100%' },
  header: { alignItems: 'center', borderBottomWidth: 1, flexDirection: 'row', minHeight: 76, paddingHorizontal: 14, paddingVertical: 11 },
  headerLogo: { borderRadius: 23, height: 46, width: 46 }, headerCopy: { flex: 1, marginLeft: 10, minWidth: 0 }, headerName: { fontSize: 14, fontWeight: '700' },
  statusRow: { alignItems: 'center', flexDirection: 'row', gap: 6, marginTop: 3 }, statusDot: { borderRadius: 5, height: 8, width: 8 }, statusText: { fontSize: 11 },
  closeButton: { alignItems: 'center', borderRadius: 18, height: 36, justifyContent: 'center', marginLeft: 8, width: 36 },
  offlineBanner: { alignItems: 'center', backgroundColor: '#FFF0ED', flexDirection: 'row', gap: 8, paddingHorizontal: 14, paddingVertical: 9 }, offlineText: { color: '#7B302A', flex: 1, fontSize: 10, lineHeight: 15 },
  conversation: { paddingBottom: 14, paddingHorizontal: 14, paddingTop: 16 }, messageRow: { alignItems: 'flex-start', flexDirection: 'row', marginBottom: 13, maxWidth: '88%' }, residentRow: { alignSelf: 'flex-end', justifyContent: 'flex-end' },
  messageAvatar: { borderRadius: 16, height: 30, marginRight: 7, marginTop: 2, width: 30 }, messageContent: { flexShrink: 1 }, messageBubble: { borderRadius: 16, borderTopLeftRadius: 5, paddingHorizontal: 13, paddingVertical: 10 }, residentBubble: { backgroundColor: assistantBlue, borderRadius: 16, borderTopRightRadius: 5 }, messageText: { fontSize: 12, lineHeight: 18 }, timestamp: { fontSize: 9, marginTop: 4 }, residentTimestamp: { textAlign: 'right' },
  suggestionsCard: { borderRadius: 15, borderWidth: 1, marginBottom: 16, marginLeft: 37, padding: 11 }, suggestionsTitle: { fontSize: 11, fontWeight: '700', marginBottom: 9 }, suggestionList: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 }, suggestion: { borderRadius: 10, borderWidth: 1, paddingHorizontal: 9, paddingVertical: 7 }, suggestionText: { fontSize: 9, fontWeight: '600' },
  composer: { alignItems: 'center', borderTopWidth: 1, flexDirection: 'row', gap: 9, paddingHorizontal: 12, paddingVertical: 11 }, input: { borderRadius: 13, borderWidth: 1, flex: 1, fontSize: 12, height: 46, paddingHorizontal: 13, paddingVertical: 9 }, sendButton: { alignItems: 'center', backgroundColor: assistantBlue, borderRadius: 13, height: 46, justifyContent: 'center', width: 46 },
});
