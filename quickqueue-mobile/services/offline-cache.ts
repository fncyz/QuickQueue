import AsyncStorage from '@react-native-async-storage/async-storage';

const ACCOUNT_KEY = 'quickqueue.accountId';
const CACHE_PREFIX = 'quickqueue.cache.';
const RECENT_PROFILE_KEY = 'quickqueue.recentProfile';

export type RecentResidentProfile = { displayName: string; username: string };

export async function saveRecentResidentProfile(profile: RecentResidentProfile) {
  await AsyncStorage.setItem(RECENT_PROFILE_KEY, JSON.stringify(profile));
}

export async function readRecentResidentProfile(): Promise<RecentResidentProfile | null> {
  try {
    const raw = await AsyncStorage.getItem(RECENT_PROFILE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<RecentResidentProfile>;
    if (!value.username || !value.displayName) return null;
    return { displayName: value.displayName, username: value.username };
  } catch {
    await AsyncStorage.removeItem(RECENT_PROFILE_KEY);
    return null;
  }
}

export async function setCurrentAccountId(username: string) {
  await AsyncStorage.setItem(ACCOUNT_KEY, username.trim().toLowerCase());
}

export async function getCurrentAccountId() {
  return AsyncStorage.getItem(ACCOUNT_KEY);
}

const scopedKey = async (name: string) => {
  const accountId = await getCurrentAccountId();
  return accountId ? `${CACHE_PREFIX}${accountId}.${name}` : null;
};

export async function writeOfflineCache<T>(name: string, value: T) {
  const key = await scopedKey(name);
  if (!key) return;
  await AsyncStorage.setItem(key, JSON.stringify({ savedAt: new Date().toISOString(), value }));
}

export async function readOfflineCache<T>(name: string): Promise<{ savedAt: string; value: T } | null> {
  const key = await scopedKey(name);
  if (!key) return null;
  try {
    const raw = await AsyncStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.savedAt !== 'string' || !('value' in parsed)) return null;
    return parsed as { savedAt: string; value: T };
  } catch {
    await AsyncStorage.removeItem(key);
    return null;
  }
}

export async function removeOfflineCache(name: string) {
  const key = await scopedKey(name);
  if (key) await AsyncStorage.removeItem(key);
}

export async function clearCurrentResidentData() {
  const accountId = await getCurrentAccountId();
  const keys = await AsyncStorage.getAllKeys();
  const accountPrefix = accountId ? `${CACHE_PREFIX}${accountId}.` : '';
  const scopedKeys = accountPrefix ? keys.filter((key) => key.startsWith(accountPrefix)) : [];
  const photoKeys = accountId ? keys.filter((key) => key.toLowerCase() === `quickqueue.profilephoto.${accountId}`) : [];
  await AsyncStorage.multiRemove([...scopedKeys, ...photoKeys, ACCOUNT_KEY]);
}
