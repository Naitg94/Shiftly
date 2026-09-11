'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Sparkles, Database, LogOut, User as UserIcon, X, Check, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface NavbarProps {
  activeTab: 'analyze' | 'memory';
  onTabChange: (tab: 'analyze' | 'memory') => void;
  onReset?: () => void;
}

export default function Navbar({ activeTab, onTabChange, onReset }: NavbarProps) {
  const { user, displayName, updateDisplayName, signOut } = useAuth();
  const router = useRouter();

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [nameSuccess, setNameSuccess] = useState<string | null>(null);

  const handleAnalyzeClick = () => {
    onTabChange('analyze');
    onReset?.();
  };

  const handleSignOut = async () => {
    setIsProfileOpen(false);
    await signOut();
    router.replace('/');
  };

  const handleOpenProfile = () => {
    setEditedName(displayName);
    setNameError(null);
    setNameSuccess(null);
    setIsProfileOpen(true);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = editedName.trim();
    if (!trimmed) {
      setNameError('Display name cannot be empty.');
      return;
    }
    if (trimmed.length < 2) {
      setNameError('Display name must be at least 2 characters long.');
      return;
    }
    if (trimmed.length > 50) {
      setNameError('Display name cannot exceed 50 characters.');
      return;
    }
    if (/[\u0000-\u001F\u007F-\u009F]/.test(trimmed)) {
      setNameError('Display name contains invalid characters.');
      return;
    }

    setIsSavingName(true);
    setNameError(null);
    setNameSuccess(null);

    const { error } = await updateDisplayName(trimmed);
    setIsSavingName(false);
    if (error) {
      setNameError(error.message);
    } else {
      setNameSuccess('Display name updated!');
      setTimeout(() => {
        setNameSuccess(null);
        setIsProfileOpen(false);
      }, 700);
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div
          onClick={handleAnalyzeClick}
          className="flex cursor-pointer items-center space-x-3 transition-opacity hover:opacity-90"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-lg shadow-md shadow-blue-500/20">
            S
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">Shiftly</span>
              <span className="text-[10px] font-medium uppercase tracking-wider rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
                Beta
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-none">Find what matters.</p>
          </div>
        </div>

        {/* Navigation Items & User Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          <nav className="flex items-center gap-2 sm:gap-3 text-sm">
            <button
              onClick={handleAnalyzeClick}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'analyze'
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Analyze</span>
            </button>

            <button
              onClick={() => onTabChange('memory')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'memory'
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
              }`}
            >
              <Database className="h-3.5 w-3.5" />
              <span>Project Memory</span>
            </button>
          </nav>

          {/* User Identity or Guest Actions */}
          {user ? (
            <div className="flex items-center gap-2 sm:gap-2.5 pl-2 sm:pl-3 border-l border-slate-800">
              <button
                onClick={handleOpenProfile}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition-colors cursor-pointer max-w-[160px]"
                title="Account profile settings"
                aria-label="Account profile settings"
              >
                <div className="h-5 w-5 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0">
                  <UserIcon className="h-3 w-3" />
                </div>
                <span className="truncate font-medium">{displayName || user.email?.split('@')[0]}</span>
              </button>

              <button
                onClick={handleSignOut}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-rose-400 text-xs transition-colors cursor-pointer"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-slate-800">
              <Link
                href="/login"
                className="px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition-colors cursor-pointer"
              >
                Log In
              </Link>
              <Link
                href="/signup"
                className="px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-500/20 transition-all cursor-pointer"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Account Profile Modal */}
      {isProfileOpen && user && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-5 sm:p-6 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <UserIcon className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-white">Account Profile</h3>
              </div>
              <button
                onClick={() => setIsProfileOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="Close profile modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-3.5">
              <div className="space-y-1">
                <label className="text-[11px] font-medium text-slate-400">
                  Email Address (Read-only)
                </label>
                <div className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl px-3 py-2 text-xs text-slate-400 select-all font-mono truncate">
                  {user.email}
                </div>
              </div>

              <div className="space-y-1">
                <label htmlFor="profile-display-name" className="text-[11px] font-semibold text-slate-300">
                  Display Name
                </label>
                <input
                  id="profile-display-name"
                  type="text"
                  required
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  placeholder="Your display name"
                  maxLength={50}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              {nameError && (
                <p className="text-[11px] text-rose-400">{nameError}</p>
              )}
              {nameSuccess && (
                <p className="text-[11px] text-emerald-400">{nameSuccess}</p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsProfileOpen(false)}
                  className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingName}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {isSavingName ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Check className="h-3 w-3" />
                  )}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
