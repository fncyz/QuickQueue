import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'quickqueue.floatingAssistantEnabled';
type AssistantPreference = { enabled: boolean; setEnabled: (enabled: boolean) => void };
const AssistantPreferenceContext = createContext<AssistantPreference>({ enabled: true, setEnabled: () => undefined });

export function AssistantPreferenceProvider({ children }: PropsWithChildren) {
  const [enabled, setEnabledState] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((value) => {
      if (value !== null) setEnabledState(value === 'true');
    });
  }, []);

  const setEnabled = (value: boolean) => {
    setEnabledState(value);
    void AsyncStorage.setItem(STORAGE_KEY, String(value));
  };

  const contextValue = useMemo(() => ({ enabled, setEnabled }), [enabled]);
  return <AssistantPreferenceContext.Provider value={contextValue}>{children}</AssistantPreferenceContext.Provider>;
}

export const useAssistantPreference = () => useContext(AssistantPreferenceContext);
