import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Poppins_400Regular } from '@expo-google-fonts/poppins/400Regular';
import { Poppins_500Medium } from '@expo-google-fonts/poppins/500Medium';
import { Poppins_600SemiBold } from '@expo-google-fonts/poppins/600SemiBold';
import { Poppins_700Bold } from '@expo-google-fonts/poppins/700Bold';
import { Poppins_800ExtraBold } from '@expo-google-fonts/poppins/800ExtraBold';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { initialWindowMetrics, SafeAreaProvider } from 'react-native-safe-area-context';
import 'react-native-reanimated';

import { AppThemeProvider, useAppTheme } from '@/contexts/app-theme';
import { ConnectivityProvider } from '@/contexts/connectivity';
import { AssistantPreferenceProvider } from '@/contexts/assistant-preference';
import { QuickQueueLoadingScreen } from '@/components/QuickQueueLoadingScreen';
import { AuthSessionProvider } from '@/contexts/auth-session';
import { PushNotificationsProvider } from '@/contexts/push-notifications';
import '@/services/startup-loading';

function AppNavigator() {
  const { isDark } = useAppTheme();
  return (
    <ThemeProvider value={isDark ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen
          name="(auth)"
          options={{ headerShown: false }}
        />

        <Stack.Screen
          name="(tabs)"
          options={{ headerShown: false }}
        />
        <Stack.Screen name="profile" options={{ headerShown: false }} />
        <Stack.Screen name="notifications" options={{ headerShown: false }} />
        <Stack.Screen name="notification-settings" options={{ headerShown: false }} />
        <Stack.Screen name="booking-success" options={{ headerShown: false }} />
        <Stack.Screen name="personal-information" options={{ headerShown: false }} />
        <Stack.Screen name="security-login" options={{ headerShown: false }} />
        <Stack.Screen
          name="modal"
          options={{
            presentation: "modal",
            title: "Modal",
          }}
        />
      </Stack>
      <StatusBar style={isDark ? 'light' : 'auto'} />
    </ThemeProvider>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({ Poppins_400Regular, Poppins_500Medium, Poppins_600SemiBold, Poppins_700Bold, Poppins_800ExtraBold });
  if (!fontsLoaded) return <QuickQueueLoadingScreen />;
  return <SafeAreaProvider initialMetrics={initialWindowMetrics}><AppThemeProvider><ConnectivityProvider><AssistantPreferenceProvider><AuthSessionProvider><PushNotificationsProvider><AppNavigator /></PushNotificationsProvider></AuthSessionProvider></AssistantPreferenceProvider></ConnectivityProvider></AppThemeProvider></SafeAreaProvider>;
}
