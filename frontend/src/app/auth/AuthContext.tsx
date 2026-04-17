import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import * as authApi from './api';
import { loadStoredAuthSession, saveStoredAuthSession, type StoredAuthSession } from './storage';
import type { User } from '../types';


export type AuthUser = User;

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  department?: string;
  companyCode?: string;
  companyName?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);


export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredAuthSession | null>(() => loadStoredAuthSession());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    saveStoredAuthSession(session);
  }, [session]);

  useEffect(() => {
    const storedSession = loadStoredAuthSession();
    if (!storedSession?.token) {
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    void authApi
      .me()
      .then((user) => {
        if (!isMounted) {
          return;
        }
        setSession({
          token: storedSession.token,
          user,
        });
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setSession(null);
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const nextSession = await authApi.login(payload);
    setSession(nextSession);
    return nextSession.user;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const nextSession = await authApi.register(payload);
    setSession(nextSession);
    return nextSession.user;
  }, []);

  const logout = useCallback(() => {
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.token && session?.user),
      isLoading,
      login,
      register,
      logout,
    }),
    [isLoading, login, logout, register, session],
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
