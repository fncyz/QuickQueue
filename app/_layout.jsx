import { Stack } from "expo-router"
import { StatusBar } from "expo-status-bar"

export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="qq/res_login" options={{ headerShown: false }} />
        <Stack.Screen name="qq/signup" options={{ headerShown: false }} />
        <Stack.Screen name="qq/res_dashboard/res_index" options={{ headerShown: false }} />
        <Stack.Screen name="qq/res_dashboard/book" options={{ headerShown: false }} />
        <Stack.Screen name="qq/res_dashboard/queue" options={{ headerShown: false }} />
        <Stack.Screen name="qq/res_dashboard/about" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/ad_index" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/appoint" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/queue" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/prio" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/walk_in" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/services" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/reports" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/announcements" options={{ headerShown: false }} />
        <Stack.Screen name="qq/admin_dashboard/settings" options={{ headerShown: false }} />
      </Stack>
    </>
  )
}
