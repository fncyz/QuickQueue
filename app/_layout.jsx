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
      </Stack>
    </>
  )
}