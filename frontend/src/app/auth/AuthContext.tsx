import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { mockUsers } from '../data/mockData';
import type { User } from '../types';

const AUTH_STORAGE_KEY = 'meetingai.auth.user';

export type AuthUser = User;

interface LoginPayload {
  name: string;
  email: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => AuthUser;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function sanitizeStoredUser(value: unknown): AuthUser | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const user = value as Partial<AuthUser>;
  if (
    typeof user.id !== 'string' ||
    typeof user.name !== 'string' ||
    typeof user.email !== 'string' ||
    typeof user.role !== 'string' ||
    typeof user.department !== 'string'
  ) {
    return null;
  }

  return {
    id: user.id,
    name: user.name,
    email: user.email,
    avatar: typeof user.avatar === 'string' ? user.avatar : undefined,
    role:
      user.role === 'admin' || user.role === 'manager' || user.role === 'member'
        ? user.role
        : 'member',
    department: user.department,
  };
}

function loadStoredUser() {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    return sanitizeStoredUser(JSON.parse(raw));
  } catch {
    return null;
  }
}

function resolveAuthUser(payload: LoginPayload) {
  const normalizedEmail = payload.email.trim().toLowerCase();
  const normalizedName = payload.name.trim().toLowerCase();

  const matchedUser =
    mockUsers.find((user) => user.email.toLowerCase() === normalizedEmail) ??
    mockUsers.find((user) => user.name.toLowerCase() === normalizedName);

  if (matchedUser) {
    return {
      ...matchedUser,
      name: payload.name.trim() || matchedUser.name,
      email: payload.email.trim() || matchedUser.email,
    } satisfies AuthUser;
  }

  return {
    id:
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? `auth-${crypto.randomUUID()}`
        : `auth-${Date.now()}`,
    name: payload.name.trim(),
    email: payload.email.trim(),
    role: 'member',
    department: 'Genel',
  } satisfies AuthUser;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => loadStoredUser());

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (!user) {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  }, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login: (payload) => {
        const nextUser = resolveAuthUser(payload);
        setUser(nextUser);
        return nextUser;
      },
      logout: () => {
        setUser(null);
      },
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}
