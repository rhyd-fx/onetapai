"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { loginUser, registerUser, verifyRegisterUser, verifyUserSession, AuthResponse, RegisterResponse } from '@/lib/api';

interface UserProfile {
  user_id: number;
  username: string;
  email: string;
  linked_riot_id?: string | null;
}

interface AuthContextType {
  user: UserProfile | null;
  isLoggedIn: boolean;
  authLoading: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<RegisterResponse>;
  verifyRegister: (email: string, code: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
  authError: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Validate session on mount
  useEffect(() => {
    async function checkSession() {
      const token = localStorage.getItem("onetap_token");
      if (!token) {
        setAuthLoading(false);
        return;
      }
      try {
        const u = await verifyUserSession();
        setUser(u);
      } catch (err) {
        console.warn("Session validation failed, clearing token", err);
        localStorage.removeItem("onetap_token");
        localStorage.removeItem("onetap_username");
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }
    checkSession();
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    setAuthError(null);
    try {
      const res: AuthResponse = await loginUser(usernameOrEmail, password);
      localStorage.setItem("onetap_token", res.token);
      localStorage.setItem("onetap_username", res.username);
      
      // Verify session immediately to load full profile
      const u = await verifyUserSession();
      setUser(u);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setAuthError(msg);
      throw err;
    }
  };

  const register = async (username: string, email: string, password: string) => {
    setAuthError(null);
    try {
      return await registerUser(username, email, password);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      setAuthError(msg);
      throw err;
    }
  };

  const verifyRegister = async (email: string, code: string) => {
    setAuthError(null);
    try {
      const res: AuthResponse = await verifyRegisterUser(email, code);
      localStorage.setItem("onetap_token", res.token);
      localStorage.setItem("onetap_username", res.username);
      
      const u = await verifyUserSession();
      setUser(u);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Verification failed";
      setAuthError(msg);
      throw err;
    }
  };

  const refreshSession = async () => {
    try {
      const u = await verifyUserSession();
      setUser(u);
    } catch (err) {
      console.warn("Failed to refresh session", err);
    }
  };

  const logout = () => {
    localStorage.removeItem("onetap_token");
    localStorage.removeItem("onetap_username");
    setUser(null);
    setAuthError(null);
  };

  const clearError = () => setAuthError(null);

  const isLoggedIn = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        authLoading,
        login,
        register,
        verifyRegister,
        logout,
        refreshSession,
        authError,
        clearError
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
