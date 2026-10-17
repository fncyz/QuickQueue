import { Ionicons } from '@expo/vector-icons';
import { forwardRef } from 'react';
import { Pressable, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { Text } from '@/components/Typography';

type HeaderNotificationBellProps = {
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  unreadCount?: number;
};

export const HeaderNotificationBell = forwardRef<React.ElementRef<typeof Pressable>, HeaderNotificationBellProps>(({ onPress, style, unreadCount = 0 }, ref) => {
  return <Pressable
    ref={ref}
    accessibilityLabel={`Open notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
    hitSlop={8}
    onPress={onPress}
    style={[style, s.button]}
  >
    <Ionicons name="notifications-outline" size={22} color="#0646A8" />
    {unreadCount > 0 && <View style={s.badge}><Text style={s.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text></View>}
  </Pressable>;
});
HeaderNotificationBell.displayName = 'HeaderNotificationBell';

const s = StyleSheet.create({
  badge: { alignItems: 'center', backgroundColor: '#EF3340', borderColor: '#FFFFFF', borderRadius: 8, borderWidth: 2, height: 16, justifyContent: 'center', minWidth: 16, paddingHorizontal: 2, position: 'absolute', right: -2, top: -2 },
  badgeText: { color: '#FFFFFF', fontSize: 8, fontWeight: '800' },
  button: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 20, height: 40, justifyContent: 'center', width: 40 },
});
