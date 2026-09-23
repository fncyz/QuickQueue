import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

const THEME_KEY = 'quickqueue.darkMode';

export const lightPalette = {
  background: '#FFFFFF', surface: '#FFFFFF', surfaceAlt: '#F3F7FD', text: '#10295E', muted: '#718098', border: '#E1E9F4', primary: '#07419C', accent: '#0873FF', iconBackground: '#EDF4FF', dangerBackground: '#FFF3F6',
};
export const darkPalette = {
  background: '#0B1220', surface: '#131E30', surfaceAlt: '#19263A', text: '#F4F7FC', muted: '#A9B7CC', border: '#2A3A52', primary: '#0B3474', accent: '#67A8FF', iconBackground: '#203553', dangerBackground: '#351D29',
};

type AppThemeContextValue = {
  isDark: boolean;
  colors: typeof lightPalette;
  setDarkMode: (enabled: boolean) => void;
};

const AppThemeContext = createContext<AppThemeContextValue>({ isDark: false, colors: lightPalette, setDarkMode: () => undefined });

export function AppThemeProvider({ children }: PropsWithChildren) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => { AsyncStorage.getItem(THEME_KEY).then((value) => setIsDark(value === 'true')); }, []);
  const setDarkMode = (enabled: boolean) => {
    setIsDark(enabled);
    AsyncStorage.setItem(THEME_KEY, String(enabled));
  };
  const value = useMemo(() => ({ isDark, colors: isDark ? darkPalette : lightPalette, setDarkMode }), [isDark]);
  return <AppThemeContext.Provider value={value}>{children}</AppThemeContext.Provider>;
}

export const useAppTheme = () => useContext(AppThemeContext);
