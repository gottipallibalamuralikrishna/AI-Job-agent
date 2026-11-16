import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { authApi } from "../api/auth.api";
import { isAxiosError } from "axios";
import { setAccessToken } from "../api/axios";

import type { User, LoginPayload, RegisterPayload } from "../types/auth";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  sessionUnavailable: boolean;
  retrySession: () => void;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionUnavailable, setSessionUnavailable] = useState(false);
  const [sessionAttempt, setSessionAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    const restoreSession = async () => {
      try {
        const result = await authApi.refresh();

        if (!active) return;

        setAccessToken(result.access_token);
        setUser(result.user);
      } catch (error) {
        if (active) {
          if (isAxiosError(error) && error.response?.status === 401) {
            setAccessToken(null);
            setUser(null);
          } else {
            setSessionUnavailable(true);
          }
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      active = false;
    };
  }, [sessionAttempt]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionUnavailable,
      retrySession: () => {
        setSessionUnavailable(false);
        setLoading(true);
        setSessionAttempt((attempt) => attempt + 1);
      },

      login: async (payload) => {
        const result = await authApi.login(payload);
        setSessionUnavailable(false);

        setAccessToken(result.access_token);
        setUser(result.user);
      },

      register: async (payload) => {
        await authApi.register(payload);
      },

      logout: async () => {
        try {
          await authApi.logout();
        } finally {
          setAccessToken(null);
          setUser(null);
        }
      },
    }),
    [user, loading, sessionUnavailable],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
