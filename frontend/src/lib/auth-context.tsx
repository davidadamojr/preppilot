'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AxiosError } from 'axios';
import { authApi } from './api';
import { User } from '@/types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, dietType: string, dietaryExclusions?: string[]) => Promise<void>;
  updateExclusions: (exclusions: string[]) => Promise<void>;
  refreshProfile: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await authApi.getProfile();
      setUser(response.data);
    } catch (error) {
      // Clear token on any auth error (401 handled by API interceptor)
      localStorage.removeItem('token');
      setToken(null);

      // Log non-401 errors for debugging (401 is expected for expired tokens)
      const axiosError = error as AxiosError;
      if (axiosError.response?.status !== 401) {
        console.error('Failed to fetch user profile:', axiosError.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    setToken(access_token);
    await fetchUser();
  };

  const register = async (email: string, password: string, dietType: string, dietaryExclusions: string[] = []) => {
    await authApi.register(email, password, dietType, dietaryExclusions);
    await login(email, password);
  };

  const updateExclusions = async (exclusions: string[]) => {
    await authApi.updateExclusions(exclusions);
    await fetchUser(); // Refresh user data
  };

  const refreshProfile = async () => {
    await fetchUser();
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, updateExclusions, refreshProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
