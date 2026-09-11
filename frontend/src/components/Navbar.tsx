'use client';

import { Sparkles, Database, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface NavbarProps {
  activeTab: 'analyze' | 'memory';
  onTabChange: (tab: 'analyze' | 'memory') => void;
  onReset?: () => void;
}

export default function Navbar({ activeTab, onTabChange, onReset }: NavbarProps) {
  const { user, signOut } = useAuth();
  const router = useRouter();

  const handleAnalyzeClick = () => {
    onTabChange('analyze');
    onReset?.();
  };

  const handleSignOut = async () => {
    await signOut();
    router.replace('/login');
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
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all ${
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
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'memory'
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
              }`}
            >
              <Database className="h-3.5 w-3.5" />
              <span>Project Memory</span>
            </button>
          </nav>

          {/* User Identity & Logout */}
          {user && (
            <div className="flex items-center gap-2.5 pl-2 sm:pl-3 border-l border-slate-800">
              <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-400 max-w-[150px] truncate" title={user.email}>
                <div className="h-6 w-6 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 shrink-0">
                  <UserIcon className="h-3 w-3" />
                </div>
                <span className="truncate">{user.email?.split('@')[0]}</span>
              </div>

              <button
                onClick={handleSignOut}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-rose-400 text-xs transition-colors"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
