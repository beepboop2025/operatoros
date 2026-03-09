import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApi } from '../api/client';
import type { User, LoginResponse } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<LoginResponse>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auditmind_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const isAuthenticated = Boolean(token && user);

  const checkAuth = useCallback(async () => {
    const stored = localStorage.getItem('auditmind_token');
    if (!stored) {
      setIsLoading(false);
      setUser(null);
      setToken(null);
      return;
    }
    try {
      setToken(stored);
      const me = await authApi.getMe();
      setUser(me);
    } catch {
      localStorage.removeItem('auditmind_token');
      localStorage.removeItem('auditmind_user');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email: string, password: string): Promise<LoginResponse> => {
    const data = await authApi.login(email, password);
    const jwt = data.access_token || data.token || '';
    localStorage.setItem('auditmind_token', jwt);
    setToken(jwt);
    // Fetch user profile
    try {
      const me = await authApi.getMe();
      setUser(me);
      localStorage.setItem('auditmind_user', JSON.stringify(me));
    } catch {
      // If getMe fails, use whatever came back from login
      const fallback: User = data.user || { id: '', email };
      setUser(fallback);
    }
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auditmind_token');
    localStorage.removeItem('auditmind_user');
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, isLoading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
