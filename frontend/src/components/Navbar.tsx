'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Sparkles, Database, LogOut } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import SettingsModal from './settings/SettingsModal';

interface NavbarProps {
  activeTab?: 'analyze' | 'memory';
  onTabChange?: (tab: 'analyze' | 'memory') => void;
  onReset?: () => void;
}

export default function Navbar({ activeTab, onTabChange, onReset }: NavbarProps) {
  const { user, username, signOut, currentPlan, isLoading } = useAuth();
  const router = useRouter();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleAnalyzeClick = () => {
    if (onTabChange) {
      onTabChange('analyze');
      onReset?.();
    } else {
      router.push('/');
    }
  };

  const handleMemoryClick = () => {
    if (onTabChange) {
      onTabChange('memory');
    } else {
      router.push('/?tab=memory');
    }
  };

  const handleSignOut = async () => {
    setIsSettingsOpen(false);
    await signOut();
    router.replace('/');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-3 sm:px-6">
        {/* Brand */}
        <div
          onClick={handleAnalyzeClick}
          className="flex cursor-pointer items-center space-x-2 sm:space-x-3 transition-opacity hover:opacity-90 shrink-0"
        >
          <img
            src="/favicon.ico"
            alt="Shiftly"
            className="h-8 w-8 sm:h-9 sm:w-9 shrink-0 object-contain"
          />
          <div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-base sm:text-lg font-bold tracking-tight text-white">Shiftly</span>
              <span className="hidden md:inline-block text-[10px] font-medium uppercase tracking-wider rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
                Beta
              </span>
              {isLoading ? (
                <div
                  className="h-5 w-14 rounded-full bg-slate-800/80 border border-slate-700/50 animate-pulse shrink-0"
                  aria-hidden="true"
                />
              ) : (
                <Link
                  href="/plans"
                  className={`inline-flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2 py-0.5 rounded-full border text-[10px] font-bold tracking-wider transition-all cursor-pointer ${
                    currentPlan === 'PRO'
                      ? 'border-cyan-500/40 bg-gradient-to-r from-blue-600/20 to-cyan-500/20 text-cyan-300 hover:text-cyan-200 hover:border-cyan-400 shadow-sm shadow-cyan-500/10'
                      : currentPlan === 'PLUS'
                      ? 'border-amber-500/40 bg-amber-500/15 text-amber-300 hover:text-amber-200 hover:border-amber-400 shadow-sm shadow-amber-500/10'
                      : currentPlan === 'FREE'
                      ? 'border-blue-500/30 bg-blue-500/10 text-blue-400 hover:text-blue-300 hover:border-blue-500/50'
                      : 'border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:border-slate-600'
                  }`}
                  title={`Current plan: ${currentPlan}. Click to view plans.`}
                  aria-label={`Plan: ${currentPlan}`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      currentPlan === 'PRO'
                        ? 'bg-cyan-400 animate-pulse'
                        : currentPlan === 'PLUS'
                        ? 'bg-amber-400'
                        : currentPlan === 'FREE'
                        ? 'bg-blue-400'
                        : 'bg-slate-400'
                    }`}
                  />
                  <span>{currentPlan}</span>
                </Link>
              )}
            </div>
            <p className="text-[11px] text-slate-400 leading-none hidden lg:block">Find what matters.</p>
          </div>
        </div>

        {/* Navigation Items & User Controls */}
        <div className="flex items-center gap-1 sm:gap-3">
          <nav className="flex items-center gap-1 sm:gap-2 text-sm">
            <button
              onClick={handleAnalyzeClick}
              className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'analyze'
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
              }`}
              title="Analyze Communication"
              aria-label="Analyze Communication"
            >
              <Sparkles className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden sm:inline">Analyze</span>
            </button>

            <button
              onClick={handleMemoryClick}
              className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                activeTab === 'memory'
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
              }`}
              title="Project Memory"
              aria-label="Project Memory"
            >
              <Database className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden md:inline">Project </span>
              <span className="hidden sm:inline">Memory</span>
            </button>

            <Link
              href="/plans"
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent transition-all cursor-pointer"
              title="Subscription & Plans"
              aria-label="Subscription & Plans"
            >
              <span>Plans</span>
            </Link>
          </nav>

          {/* User Identity or Guest Actions */}
          {isLoading ? (
            <div className="flex items-center gap-1 sm:gap-2 pl-1 sm:pl-2.5 border-l border-slate-800">
              <div className="h-7 w-20 sm:w-28 rounded-lg bg-slate-800/60 border border-slate-800/60 animate-pulse shrink-0" />
            </div>
          ) : user ? (
            <div className="flex items-center gap-1 sm:gap-2 pl-1 sm:pl-2.5 border-l border-slate-800">
              <button
                onClick={() => setIsSettingsOpen(true)}
                className="flex items-center gap-1.5 px-1.5 sm:px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition-colors cursor-pointer max-w-[85px] sm:max-w-[160px]"
                title="Shiftly Settings"
                aria-label="Shiftly Settings"
              >
                <div className="h-5 w-5 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 text-[10px] font-bold">
                  {username ? username.charAt(0).toUpperCase() : (user.email?.charAt(0).toUpperCase() || 'U')}
                </div>
                <span className="truncate font-medium">{username || user.email?.split('@')[0]}</span>
              </button>

              <button
                onClick={handleSignOut}
                className="inline-flex items-center gap-1 px-1.5 sm:px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-rose-400 text-xs transition-colors cursor-pointer shrink-0"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1 sm:gap-2 pl-1 sm:pl-2.5 border-l border-slate-800">
              <Link
                href="/login"
                className="px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-xl text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition-colors cursor-pointer whitespace-nowrap"
              >
                Log In
              </Link>
              <Link
                href="/signup"
                className="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-xl text-xs sm:text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-500/20 transition-all cursor-pointer whitespace-nowrap"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </header>
  );
}
