'use client';

import { Search, Palette, CreditCard, BarChart3, HardDrive, User, LogOut } from 'lucide-react';

export type SettingsSection = 'general' | 'billing' | 'usage' | 'storage' | 'account';

export interface SettingsNavItem {
  id: SettingsSection;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  keywords: string[];
}

export const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  {
    id: 'general',
    label: 'General',
    icon: Palette,
    keywords: ['general', 'appearance', 'theme', 'dark', 'light', 'system', 'font', 'accent', 'color', 'text size', 'typography', 'animations', 'motion', 'reduced motion', 'reset'],
  },
  {
    id: 'billing',
    label: 'Billing',
    icon: CreditCard,
    keywords: ['billing', 'plan', 'invoices', 'payment', 'subscription', 'free', 'pricing'],
  },
  {
    id: 'usage',
    label: 'Usage',
    icon: BarChart3,
    keywords: ['usage', 'analyses', 'projects', 'characters', 'inputs', 'pdf', 'docx', 'txt', 'whatsapp', 'eml', 'mbox', 'zip', 'limits', 'quota'],
  },
  {
    id: 'storage',
    label: 'Storage',
    icon: HardDrive,
    keywords: ['storage', 'project memory', 'memory', 'key points', 'actions', 'decisions', 'dates', 'privacy', 'mb', 'stored'],
  },
  {
    id: 'account',
    label: 'Account',
    icon: User,
    keywords: ['account', 'username', 'email', 'user id', 'uuid', 'password', 'delete', 'danger zone', 'sign out'],
  },
];

interface SettingsSidebarProps {
  activeSection: SettingsSection;
  onSelectSection: (section: SettingsSection) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  username: string;
  email?: string;
  onSignOut: () => void;
}

export default function SettingsSidebar({
  activeSection,
  onSelectSection,
  searchQuery,
  onSearchChange,
  username,
  email,
  onSignOut,
}: SettingsSidebarProps) {
  const cleanQuery = searchQuery.trim().toLowerCase();

  const filteredItems = cleanQuery
    ? SETTINGS_NAV_ITEMS.filter(
        (item) =>
          item.label.toLowerCase().includes(cleanQuery) ||
          item.keywords.some((k) => k.includes(cleanQuery))
      )
    : SETTINGS_NAV_ITEMS;

  return (
    <aside className="hidden md:flex md:w-60 shrink-0 flex-col justify-between border-r border-slate-800 bg-slate-950/60 p-4 overflow-y-auto">
      <div className="space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search settings..."
            className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* 5 Flat Selectable Navigation Items */}
        <nav className="space-y-1">
          {filteredItems.length === 0 ? (
            <div className="text-center py-4 text-xs text-slate-500">
              No matching settings found.
            </div>
          ) : (
            filteredItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectSection(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left cursor-pointer ${
                    isActive
                      ? 'bg-blue-600 text-white font-semibold shadow-sm shadow-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })
          )}
        </nav>
      </div>

      {/* User info & Sign Out at bottom of sidebar (Desktop) */}
      <div className="hidden md:block pt-4 border-t border-slate-800/80 mt-4 space-y-2">
        <div className="flex items-center gap-2 px-1">
          <div className="h-6 w-6 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-[10px] font-bold text-blue-400 shrink-0">
            {username ? username.charAt(0).toUpperCase() : (email?.charAt(0).toUpperCase() || 'U')}
          </div>
          <span className="text-xs font-semibold text-slate-200 truncate">
            {username || email?.split('@')[0]}
          </span>
        </div>
        <button
          type="button"
          onClick={onSignOut}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-rose-400 hover:bg-slate-900 transition-colors cursor-pointer"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
