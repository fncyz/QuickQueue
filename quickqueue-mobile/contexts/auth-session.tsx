import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

type AuthSessionValue = { isUnlocked: boolean; lock: () => void; unlock: () => void };
const AuthSessionContext = createContext<AuthSessionValue>({ isUnlocked: false, lock: () => undefined, unlock: () => undefined });

/**
 * This state intentionally stays in memory. A full process restart resets it,
 * requiring the saved user to authenticate before protected tabs can mount.
 */
export function AuthSessionProvider({ children }: PropsWithChildren) {
  const [isUnlocked, setUnlocked] = useState(false);
  const value = useMemo(() => ({ isUnlocked, lock: () => setUnlocked(false), unlock: () => setUnlocked(true) }), [isUnlocked]);
  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export const useAuthSession = () => useContext(AuthSessionContext);
