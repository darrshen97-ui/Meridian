import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import type { Profile } from "./api/types";

interface AuthState {
  me: Profile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (displayName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Profile>("/api/auth/me")
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setMe(await api.post<Profile>("/api/auth/login", { email, password }));
  }, []);

  const register = useCallback(
    async (displayName: string, email: string, password: string) => {
      setMe(await api.post<Profile>("/api/auth/register", {
        display_name: displayName, email, password,
      }));
    }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/api/auth/logout");
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) throw err;
    }
    setMe(null);
  }, []);

  return (
    <AuthContext.Provider value={{ me, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
