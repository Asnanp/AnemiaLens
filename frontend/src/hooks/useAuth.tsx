/**
 * Auth API client and React context for AnemiaLens.
 *
 * Manages JWT access/refresh tokens, user profile, and login state.
 * Tokens are stored in localStorage and auto-refreshed on expiry.
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { endpoint, setTokenAccessor } from '../api';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UserProfile {
  uid: string;
  email: string;
  full_name: string | null;
  role: string;
  subscription_tier: string;
  scan_count: number;
  created_at: string;
  last_login_at: string | null;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  getAccessToken: () => string | null;
}

// ── Token storage ─────────────────────────────────────────────────────────────

const TOKEN_KEY = 'anemialens.tokens';

function saveTokens(tokens: TokenPair) {
  try {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  } catch { /* ignore */ }
}

function loadTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearTokens() {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Fetch profile ───────────────────────────────────────────────────────
  const fetchProfile = useCallback(async (accessToken: string): Promise<UserProfile | null> => {
    try {
      const res = await fetch(endpoint('/api/auth/me'), {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) return null;
      return (await res.json()) as UserProfile;
    } catch {
      return null;
    }
  }, []);

  // ── Refresh token ──────────────────────────────────────────────────────
  const refreshAccessToken = useCallback(async (): Promise<TokenPair | null> => {
    const tokens = loadTokens();
    if (!tokens?.refresh_token) return null;
    try {
      const res = await fetch(endpoint('/api/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });
      if (!res.ok) return null;
      const data = (await res.json()) as TokenPair;
      saveTokens(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  // ── Schedule token refresh ─────────────────────────────────────────────
  const scheduleRefresh = useCallback((expiresIn: number) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    // Refresh 2 minutes before expiry (or 30s for short-lived tokens)
    const delay = Math.max((expiresIn - 120) * 1000, 30_000);
    refreshTimer.current = setTimeout(async () => {
      const newTokens = await refreshAccessToken();
      if (newTokens) {
        scheduleRefresh(newTokens.expires_in);
      } else {
        // Refresh failed — log out
        setUser(null);
        clearTokens();
      }
    }, delay);
  }, [refreshAccessToken]);

  const completeAuth = useCallback(async (tokens: TokenPair) => {
    saveTokens(tokens);
    const profile = await fetchProfile(tokens.access_token);
    setUser(profile);
    scheduleRefresh(tokens.expires_in);
  }, [fetchProfile, scheduleRefresh]);

  // ── Init: restore session from stored tokens ───────────────────────────
  useEffect(() => {
    (async () => {
      const tokens = loadTokens();
      if (tokens?.access_token) {
        const profile = await fetchProfile(tokens.access_token);
        if (profile) {
          setUser(profile);
          scheduleRefresh(tokens.expires_in || 3600);
        } else {
          // Token expired — try refresh
          const refreshed = await refreshAccessToken();
          if (refreshed) {
            const profile2 = await fetchProfile(refreshed.access_token);
            if (profile2) {
              setUser(profile2);
              scheduleRefresh(refreshed.expires_in);
            }
          } else {
            clearTokens();
          }
        }
      }
      setIsLoading(false);
    })();

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, [fetchProfile, refreshAccessToken, scheduleRefresh]);

  // ── Login ──────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const normalizedEmail = email.trim().toLowerCase();
      const res = await fetch(endpoint('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: normalizedEmail, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      await completeAuth(data as TokenPair);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [completeAuth]);

  const loginWithGoogle = useCallback(async (credential: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const res = await fetch(endpoint('/api/auth/google'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Google sign-in failed');

      await completeAuth(data as TokenPair);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google sign-in failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [completeAuth]);

  // ── Register ───────────────────────────────────────────────────────────
  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const normalizedEmail = email.trim().toLowerCase();
      const normalizedFullName = fullName?.trim() || null;
      const res = await fetch(endpoint('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: normalizedEmail, password, full_name: normalizedFullName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Registration failed');

      await completeAuth(data as TokenPair);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [completeAuth]);

  // ── Logout ─────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const getAccessToken = useCallback(() => {
    return loadTokens()?.access_token ?? null;
  }, []);

  // Wire token accessor so api.ts can attach auth headers automatically
  useEffect(() => {
    setTokenAccessor(getAccessToken);
  }, [getAccessToken]);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      error,
      login,
      loginWithGoogle,
      register,
      logout,
      clearError,
      getAccessToken,
    }}>
      {children}
    </AuthContext.Provider>
  );
}
