'use client';

import { useState, useEffect, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { X, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { usePreferences } from '@/context/PreferencesContext';
import SettingsSidebar, { SettingsSection, SETTINGS_NAV_ITEMS } from './SettingsSidebar';
import GeneralSettings from './GeneralSettings';
import BillingSettings from './BillingSettings';
import UsageSettings from './UsageSettings';
import StorageSettings from './StorageSettings';
import AccountSettings from './AccountSettings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const emptySubscribe = () => () => {};

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { user, username, signOut } = useAuth();
  const { rememberLastSection, lastSection, setLastSection } = usePreferences();

  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);

  const targetSection: SettingsSection =
    rememberLastSection && lastSection && ['general', 'billing', 'usage', 'storage', 'account'].includes(lastSection)
      ? (lastSection as SettingsSection)
      : 'general';

  const [activeSection, setActiveSection] = useState<SettingsSection>(targetSection);
  const [prevIsOpen, setPrevIsOpen] = useState(false);

  if (isOpen && !prevIsOpen) {
    setPrevIsOpen(true);
    setActiveSection(targetSection);
  } else if (!isOpen && prevIsOpen) {
    setPrevIsOpen(false);
  }

  const [searchQuery, setSearchQuery] = useState('');

  const handleSelectSection = (section: SettingsSection) => {
    setActiveSection(section);
    if (rememberLastSection) {
      setLastSection(section);
    }
  };

  // Body scroll lock & scroll position preservation
  useEffect(() => {
    if (!isOpen) return;

    const scrollY = window.scrollY;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
      window.scrollTo(0, scrollY);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !user || !mounted) return null;

  const handleSignOut = async () => {
    onClose();
    await signOut();
  };

  const cleanQuery = searchQuery.trim().toLowerCase();
  const mobileFilteredSections = cleanQuery
    ? SETTINGS_NAV_ITEMS.filter(
        (s) => s.label.toLowerCase().includes(cleanQuery) || s.keywords.some((k) => k.includes(cleanQuery))
      )
    : SETTINGS_NAV_ITEMS;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      aria-hidden="false"
    >
      <div
        className="w-full max-w-[1050px] h-[min(800px,calc(100vh-48px))] max-h-[calc(100vh-48px)] flex flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 m-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-slate-800 bg-slate-950/80 shrink-0">
          <div className="flex items-center gap-2.5">
            <img src="/favicon.ico" alt="Shiftly" className="h-7 w-7 shrink-0 object-contain" />
            <h1 id="settings-modal-title" className="text-sm font-bold text-white tracking-tight">
              Shiftly Settings
            </h1>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Close settings"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Mobile Navigation & Search (< md) */}
        <div className="md:hidden border-b border-slate-800 bg-slate-950/80 p-3 space-y-2.5 shrink-0">
          <div className="relative">
            <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search settings..."
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 scrollbar-none">
            {mobileFilteredSections.length === 0 ? (
              <span className="text-xs text-slate-500 py-1">No matching sections</span>
            ) : (
              mobileFilteredSections.map((sec) => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => handleSelectSection(sec.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                    activeSection === sec.id
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                      : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {sec.label}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Modal Body: Sidebar (desktop) + Content (desktop/mobile) */}
        <div className="flex-1 min-h-0 flex flex-col md:flex-row overflow-hidden">
          {/* Desktop Left Sidebar with 5 Direct Items */}
          <SettingsSidebar
            activeSection={activeSection}
            onSelectSection={handleSelectSection}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            username={username}
            email={user.email}
            onSignOut={handleSignOut}
          />

          {/* Right Content Pane */}
          <main className="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 md:p-8 bg-slate-900/60">
            <div className="max-w-3xl mx-auto">
              {activeSection === 'general' && <GeneralSettings />}
              {activeSection === 'billing' && <BillingSettings />}
              {activeSection === 'usage' && <UsageSettings />}
              {activeSection === 'storage' && <StorageSettings />}
              {activeSection === 'account' && <AccountSettings onSignOut={handleSignOut} />}
            </div>
          </main>
        </div>
      </div>
    </div>,
    document.body
  );
}
