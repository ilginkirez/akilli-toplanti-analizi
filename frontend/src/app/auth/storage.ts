import type { User } from '../types';


export const AUTH_STORAGE_KEY = 'meetingai.auth.session';

export interface StoredAuthSession {
  token: string;
  user: User;
}

export function loadStoredAuthSession(): StoredAuthSession | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<StoredAuthSession>;
    if (
      !parsed ||
      typeof parsed !== 'object' ||
      typeof parsed.token !== 'string' ||
      typeof parsed.user !== 'object' ||
      parsed.user === null
    ) {
      return null;
    }
    return parsed as StoredAuthSession;
  } catch {
    return null;
  }
}

export function saveStoredAuthSession(session: StoredAuthSession | null) {
  if (typeof window === 'undefined') {
    return;
  }

  if (!session) {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}
