'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session, AuthError } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabaseClient';
import { getAccountSummary } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  username: string;
  displayName: string; // Backward compatibility alias
  currentPlan: 'GUEST' | 'FREE' | 'PLUS' | 'PRO';
  refreshPlan: () => Promise<void>;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signUp: (email: string, password: string, username?: string) => Promise<{ error: AuthError | null; user: User | null }>;
  signOut: () => Promise<{ error: AuthError | null }>;
  updateUsername: (username: string) => Promise<{ error: AuthError | null }>;
  updateDisplayName: (name: string) => Promise<{ error: AuthError | null }>; // Backward compatibility alias
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [currentPlan, setCurrentPlan] = useState<'GUEST' | 'FREE' | 'PLUS' | 'PRO'>('GUEST');
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserPlan = async (token?: string) => {
    try {
      const activeToken = token || session?.access_token;
      if (!activeToken) {
        setCurrentPlan('GUEST');
        return;
      }
      const res = await getAccountSummary(activeToken);
      if (res?.plan?.id) {
        setCurrentPlan(res.plan.id.toUpperCase() as 'FREE' | 'PLUS' | 'PRO');
      }
    } catch {
      if (session?.user) {
        setCurrentPlan('FREE');
      } else {
        setCurrentPlan('GUEST');
      }
    }
  };

  useEffect(() => {
    // 1. Check initial active session
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user && session?.access_token) {
        await fetchUserPlan(session.access_token);
      } else {
        setCurrentPlan('GUEST');
      }
      setIsLoading(false);
    });

    // 2. Listen for auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user && session?.access_token) {
        await fetchUserPlan(session.access_token);
      } else {
        setCurrentPlan('GUEST');
      }
      setIsLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const username =
    user?.user_metadata?.username ||
    user?.user_metadata?.display_name ||
    user?.user_metadata?.name ||
    user?.email?.split('@')[0] ||
    '';

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  };

  const signUp = async (email: string, password: string, username?: string) => {
    const trimmedUsername = username?.trim();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: trimmedUsername ? { username: trimmedUsername } : {},
      },
    });
    return { error, user: data.user };
  };

  const signOut = async () => {
    setCurrentPlan('GUEST');
    const { error } = await supabase.auth.signOut();
    return { error };
  };

  const updateUsername = async (name: string) => {
    const trimmed = name.trim();
    const { data, error } = await supabase.auth.updateUser({
      data: { username: trimmed },
    });
    if (!error && data.user) {
      setUser(data.user);
    }
    return { error };
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        username,
        displayName: username,
        currentPlan,
        refreshPlan: fetchUserPlan,
        isLoading,
        signIn,
        signUp,
        signOut,
        updateUsername,
        updateDisplayName: updateUsername,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
