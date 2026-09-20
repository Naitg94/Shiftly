'use client';

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from 'react';
import { deriveAccentPalette } from '@/lib/colorUtils';
import { useAuth } from '@/context/AuthContext';
import { supabase } from '@/lib/supabaseClient';

export type ThemeOption = 'dark' | 'light' | 'system';
export type AccentOption =
  | 'blue'
  | 'cyan'
  | 'violet'
  | 'purple'
  | 'emerald'
  | 'teal'
  | 'amber'
  | 'rose'
  | 'custom';
export type FontOption = 'default' | 'mono' | 'system';
export type TextSizeOption = 'small' | 'default' | 'large';

export interface AppearanceSettings {
  theme: ThemeOption;
  accent: AccentOption;
  customAccent: string | null;
  font: FontOption;
  textSize: TextSizeOption;
  animations: boolean;
  reduceMotion: boolean;
  rememberLastSection: boolean;
  lastSection: string | null;
  updatedAt?: string;
}

// Backward-compatible alias for existing components
export interface PreferencesState extends AppearanceSettings {
  accentColor: AccentOption;
  customAccentColor?: string;
  animationsEnabled: boolean;
}

export const DEFAULT_APPEARANCE: AppearanceSettings = {
  theme: 'system',
  accent: 'blue',
  customAccent: null,
  font: 'default',
  textSize: 'default',
  animations: true,
  reduceMotion: false,
  rememberLastSection: true,
  lastSection: null,
};

// Storage Keys
const GUEST_STORAGE_KEY = 'shiftly:appearance:guest';
const USER_STORAGE_PREFIX = 'shiftly:appearance:user:';
const LEGACY_STORAGE_KEY = 'shiftly_preferences';

function getIdentityStorageKey(userId: string | null | undefined): string {
  return userId ? `${USER_STORAGE_PREFIX}${userId}` : GUEST_STORAGE_KEY;
}

export interface PreferencesContextType extends PreferencesState {
  setTheme: (theme: ThemeOption) => void;
  setAccent: (accent: AccentOption) => void;
  setAccentColor: (accent: AccentOption) => void;
  setCustomAccent: (color: string | null) => void;
  setCustomAccentColor: (color: string) => void;
  setFont: (font: FontOption) => void;
  setTextSize: (size: TextSizeOption) => void;
  setAnimations: (enabled: boolean) => void;
  setAnimationsEnabled: (enabled: boolean) => void;
  setReduceMotion: (reduce: boolean) => void;
  setRememberLastSection: (remember: boolean) => void;
  setLastSection: (section: string | null) => void;
  resetAppearance: () => void;
  resolvedTheme: 'dark' | 'light';
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

function applyPreferencesToDom(prefs: AppearanceSettings, resolvedTheme: 'dark' | 'light') {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  root.setAttribute('data-theme', resolvedTheme);
  root.setAttribute('data-accent', prefs.accent);
  root.setAttribute('data-font', prefs.font);
  root.setAttribute('data-text-size', prefs.textSize);
  root.setAttribute('data-animations', String(prefs.animations));
  root.setAttribute('data-reduce-motion', String(prefs.reduceMotion));

  if (prefs.accent === 'custom' && prefs.customAccent) {
    const tokens = deriveAccentPalette(
      prefs.customAccent || '#2563EB',
      resolvedTheme === 'dark'
    );
    root.style.setProperty('--accent', tokens.accent);
    root.style.setProperty('--accent-hover', tokens.accentHover);
    root.style.setProperty('--accent-active', tokens.accentActive);
    root.style.setProperty('--accent-soft', tokens.accentSoft);
    root.style.setProperty('--accent-soft-hover', tokens.accentSoftHover);
    root.style.setProperty('--accent-border', tokens.accentBorder);
    root.style.setProperty('--accent-text', tokens.accentText);
    root.style.setProperty('--accent-ring', tokens.accentRing);
    root.style.setProperty('--accent-contrast', tokens.accentContrast);
  } else {
    root.style.removeProperty('--accent');
    root.style.removeProperty('--accent-hover');
    root.style.removeProperty('--accent-active');
    root.style.removeProperty('--accent-soft');
    root.style.removeProperty('--accent-soft-hover');
    root.style.removeProperty('--accent-border');
    root.style.removeProperty('--accent-text');
    root.style.removeProperty('--accent-ring');
    root.style.removeProperty('--accent-contrast');
  }
}

function normalizeAppearance(raw: Record<string, unknown> | null | undefined): AppearanceSettings {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_APPEARANCE };
  const rawTheme = typeof raw.theme === 'string' ? raw.theme : '';
  const rawAccent = typeof raw.accent === 'string' ? raw.accent : (typeof raw.accentColor === 'string' ? raw.accentColor : '');
  const rawFont = typeof raw.font === 'string' ? raw.font : '';
  const rawTextSize = typeof raw.textSize === 'string' ? raw.textSize : '';
  const rawCustomAccent = typeof raw.customAccent === 'string' ? raw.customAccent : (typeof raw.customAccentColor === 'string' ? raw.customAccentColor : null);

  return {
    theme: ['dark', 'light', 'system'].includes(rawTheme) ? (rawTheme as ThemeOption) : DEFAULT_APPEARANCE.theme,
    accent: ['blue', 'cyan', 'violet', 'purple', 'emerald', 'teal', 'amber', 'rose', 'custom'].includes(rawAccent)
      ? (rawAccent as AccentOption)
      : DEFAULT_APPEARANCE.accent,
    customAccent: rawCustomAccent,
    font: ['default', 'mono', 'system'].includes(rawFont) ? (rawFont as FontOption) : DEFAULT_APPEARANCE.font,
    textSize: ['small', 'default', 'large'].includes(rawTextSize) ? (rawTextSize as TextSizeOption) : DEFAULT_APPEARANCE.textSize,
    animations: raw.animations !== undefined ? Boolean(raw.animations) : (raw.animationsEnabled !== undefined ? Boolean(raw.animationsEnabled) : DEFAULT_APPEARANCE.animations),
    reduceMotion: raw.reduceMotion !== undefined ? Boolean(raw.reduceMotion) : DEFAULT_APPEARANCE.reduceMotion,
    rememberLastSection: raw.rememberLastSection !== undefined ? Boolean(raw.rememberLastSection) : DEFAULT_APPEARANCE.rememberLastSection,
    lastSection: typeof raw.lastSection === 'string' ? raw.lastSection : null,
    updatedAt: typeof raw.updatedAt === 'string' ? raw.updatedAt : undefined,
  };
}

function resolveAppearanceForIdentity(
  userId: string | null,
  metadataAppearance: unknown
): AppearanceSettings {
  if (typeof window === 'undefined') return { ...DEFAULT_APPEARANCE };

  if (!userId) {
    try {
      const guestSaved = localStorage.getItem(GUEST_STORAGE_KEY);
      if (guestSaved) {
        return normalizeAppearance(JSON.parse(guestSaved));
      }
    } catch {}
    return { ...DEFAULT_APPEARANCE };
  }

  if (metadataAppearance && typeof metadataAppearance === 'object') {
    return normalizeAppearance(metadataAppearance as Record<string, unknown>);
  }

  const userStorageKey = getIdentityStorageKey(userId);
  try {
    const cached = localStorage.getItem(userStorageKey);
    if (cached) {
      return normalizeAppearance(JSON.parse(cached));
    }
  } catch {}

  return {
    ...DEFAULT_APPEARANCE,
    updatedAt: new Date().toISOString(),
  };
}

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading: isAuthLoading } = useAuth();
  const currentUserId = user?.id || null;

  const [prevUserId, setPrevUserId] = useState<string | null | undefined>(undefined);
  const [appearance, setAppearance] = useState<AppearanceSettings>(() => {
    return resolveAppearanceForIdentity(currentUserId, user?.user_metadata?.appearance);
  });

  // Adjust state during render if identity changes
  if (prevUserId !== currentUserId) {
    setPrevUserId(currentUserId);
    const resolved = resolveAppearanceForIdentity(currentUserId, user?.user_metadata?.appearance);
    setAppearance(resolved);
  }

  const [systemDark, setSystemDark] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  const activeIdentityRef = useRef<string | null>(currentUserId);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Keep activeIdentityRef in sync
  useEffect(() => {
    activeIdentityRef.current = currentUserId;
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, [currentUserId]);

  // Track system dark mode changes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    media.addEventListener('change', handler);
    return () => media.removeEventListener('change', handler);
  }, []);

  const resolvedTheme: 'dark' | 'light' =
    appearance.theme === 'system'
      ? systemDark
        ? 'dark'
        : 'light'
      : appearance.theme;

  // Apply to DOM whenever appearance or resolvedTheme changes
  useEffect(() => {
    applyPreferencesToDom(appearance, resolvedTheme);
  }, [appearance, resolvedTheme]);

  // Synchronize initial authenticated appearance to server if not present
  useEffect(() => {
    if (isAuthLoading || !currentUserId) return;

    const userStorageKey = getIdentityStorageKey(currentUserId);
    const serverAppearance = user?.user_metadata?.appearance;

    if (!serverAppearance) {
      try {
        localStorage.setItem(userStorageKey, JSON.stringify(appearance));
      } catch {}
      supabase.auth.updateUser({
        data: { appearance },
      }).catch(() => {});
    }
  }, [currentUserId, isAuthLoading, appearance, user?.user_metadata?.appearance]);

  // Clean up legacy global key on mount if present
  useEffect(() => {
    try {
      if (localStorage.getItem(LEGACY_STORAGE_KEY)) {
        localStorage.removeItem(LEGACY_STORAGE_KEY);
      }
    } catch {}
  }, []);

  // Helper to persist to localStorage & Supabase
  const persistAppearance = useCallback((newSettings: AppearanceSettings) => {
    const key = getIdentityStorageKey(activeIdentityRef.current);
    try {
      localStorage.setItem(key, JSON.stringify(newSettings));
    } catch {}

    if (activeIdentityRef.current) {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(async () => {
        try {
          await supabase.auth.updateUser({
            data: { appearance: newSettings },
          });
        } catch (err) {
          console.warn('Failed to sync appearance to Supabase user metadata', err);
        }
      }, 500);
    }
  }, []);

  const updatePreference = useCallback(
    <K extends keyof AppearanceSettings>(key: K, value: AppearanceSettings[K]) => {
      setAppearance((prev) => {
        const updated: AppearanceSettings = {
          ...prev,
          [key]: value,
          updatedAt: new Date().toISOString(),
        };
        persistAppearance(updated);
        return updated;
      });
    },
    [persistAppearance]
  );

  const setTheme = useCallback(
    (theme: ThemeOption) => updatePreference('theme', theme),
    [updatePreference]
  );
  const setAccent = useCallback(
    (accent: AccentOption) => updatePreference('accent', accent),
    [updatePreference]
  );
  const setAccentColor = useCallback(
    (accent: AccentOption) => updatePreference('accent', accent),
    [updatePreference]
  );
  const setCustomAccent = useCallback(
    (customColor: string | null) => updatePreference('customAccent', customColor),
    [updatePreference]
  );
  const setCustomAccentColor = useCallback(
    (customColor: string) => updatePreference('customAccent', customColor),
    [updatePreference]
  );
  const setFont = useCallback(
    (font: FontOption) => updatePreference('font', font),
    [updatePreference]
  );
  const setTextSize = useCallback(
    (textSize: TextSizeOption) => updatePreference('textSize', textSize),
    [updatePreference]
  );
  const setAnimations = useCallback(
    (animations: boolean) => updatePreference('animations', animations),
    [updatePreference]
  );
  const setAnimationsEnabled = useCallback(
    (animationsEnabled: boolean) => updatePreference('animations', animationsEnabled),
    [updatePreference]
  );
  const setReduceMotion = useCallback(
    (reduceMotion: boolean) => updatePreference('reduceMotion', reduceMotion),
    [updatePreference]
  );
  const setRememberLastSection = useCallback(
    (rememberLastSection: boolean) => updatePreference('rememberLastSection', rememberLastSection),
    [updatePreference]
  );
  const setLastSection = useCallback(
    (lastSection: string | null) => updatePreference('lastSection', lastSection),
    [updatePreference]
  );

  const resetAppearance = useCallback(() => {
    const defaultSettings: AppearanceSettings = {
      ...DEFAULT_APPEARANCE,
      updatedAt: new Date().toISOString(),
    };
    setAppearance(defaultSettings);

    const key = getIdentityStorageKey(activeIdentityRef.current);
    try {
      localStorage.setItem(key, JSON.stringify(defaultSettings));
    } catch {}

    if (activeIdentityRef.current) {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      supabase.auth.updateUser({
        data: { appearance: defaultSettings },
      }).catch((err) => {
        console.warn('Failed to sync reset appearance to Supabase', err);
      });
    }
  }, []);

  return (
    <PreferencesContext.Provider
      value={{
        ...appearance,
        accentColor: appearance.accent,
        customAccentColor: appearance.customAccent || undefined,
        animationsEnabled: appearance.animations,
        setTheme,
        setAccent,
        setAccentColor,
        setCustomAccent,
        setCustomAccentColor,
        setFont,
        setTextSize,
        setAnimations,
        setAnimationsEnabled,
        setReduceMotion,
        setRememberLastSection,
        setLastSection,
        resetAppearance,
        resolvedTheme,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextType {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
}
