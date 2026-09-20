'use client';

import { useState, useRef } from 'react';
import { Moon, Sun, Monitor, Check, Sparkles, EyeOff, Bookmark, RotateCcw, Palette } from 'lucide-react';
import { usePreferences, AccentOption, FontOption, TextSizeOption } from '@/context/PreferencesContext';
import { useAuth } from '@/context/AuthContext';
import SettingsPlanBadge from './SettingsPlanBadge';
import ResetAppearanceDialog from './ResetAppearanceDialog';

const ACCENT_COLORS: { id: AccentOption; name: string; hex: string }[] = [
  { id: 'blue', name: 'Blue', hex: '#2563EB' },
  { id: 'cyan', name: 'Cyan', hex: '#0891B2' },
  { id: 'violet', name: 'Violet', hex: '#7C3AED' },
  { id: 'purple', name: 'Purple', hex: '#9333EA' },
  { id: 'emerald', name: 'Emerald', hex: '#059669' },
  { id: 'teal', name: 'Teal', hex: '#0D9488' },
  { id: 'amber', name: 'Amber', hex: '#D97706' },
  { id: 'rose', name: 'Rose', hex: '#E11D48' },
];

const FONTS: { id: FontOption; label: string; desc: string }[] = [
  { id: 'default', label: 'Default', desc: 'Geist / Inter' },
  { id: 'mono', label: 'Mono', desc: 'Geist Mono' },
  { id: 'system', label: 'System', desc: 'System UI' },
];

const TEXT_SIZES: { id: TextSizeOption; label: string; desc: string }[] = [
  { id: 'small', label: 'Small', desc: '14px' },
  { id: 'default', label: 'Default', desc: '16px' },
  { id: 'large', label: 'Large', desc: '17.5px' },
];

export default function GeneralSettings() {
  const {
    theme,
    setTheme,
    accentColor,
    setAccentColor,
    customAccentColor,
    setCustomAccentColor,
    font,
    setFont,
    textSize,
    setTextSize,
    animationsEnabled,
    setAnimationsEnabled,
    reduceMotion,
    setReduceMotion,
    rememberLastSection,
    setRememberLastSection,
    resetAppearance,
  } = usePreferences();

  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);
  const colorInputRef = useRef<HTMLInputElement>(null);

  const handleConfirmReset = () => {
    resetAppearance();
    setIsResetDialogOpen(false);
    setResetSuccessMessage('Appearance preferences have been reset to defaults.');
    setTimeout(() => setResetSuccessMessage(null), 3000);
  };

  const { currentPlan } = useAuth();
  const activeCustomColor = customAccentColor || '#2563EB';

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header with Plan Badge */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">General</h2>
          <p className="text-xs text-slate-400 mt-0.5">Customize how Shiftly looks and behaves.</p>
        </div>
        <SettingsPlanBadge plan={currentPlan} />
      </div>

      {resetSuccessMessage && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 animate-in fade-in duration-150">
          {resetSuccessMessage}
        </div>
      )}

      {/* Theme Selector */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold text-slate-300">Theme</label>
        <div className="grid grid-cols-3 gap-2.5">
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
              theme === 'light'
                ? 'bg-blue-600/10 border-blue-500 text-white shadow-sm shadow-blue-500/10 font-semibold'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
            }`}
          >
            <Sun className="h-4 w-4" />
            <span>Light</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
              theme === 'dark'
                ? 'bg-blue-600/10 border-blue-500 text-white shadow-sm shadow-blue-500/10 font-semibold'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
            }`}
          >
            <Moon className="h-4 w-4" />
            <span>Dark</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme('system')}
            className={`flex flex-col items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
              theme === 'system'
                ? 'bg-blue-600/10 border-blue-500 text-white shadow-sm shadow-blue-500/10 font-semibold'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
            }`}
          >
            <Monitor className="h-4 w-4" />
            <span>System</span>
          </button>
        </div>
      </div>

      {/* Accent Color */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-300">Accent Color</label>
          <span className="text-[11px] text-slate-400 font-mono">
            {accentColor === 'custom' ? `Custom (${activeCustomColor})` : ACCENT_COLORS.find(a => a.id === accentColor)?.name}
          </span>
        </div>

        {/* Palettes Grid */}
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
          {ACCENT_COLORS.map((accent) => {
            const isSelected = accentColor === accent.id;
            return (
              <button
                key={accent.id}
                type="button"
                onClick={() => setAccentColor(accent.id)}
                className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-slate-600 text-white font-semibold shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                }`}
              >
                <span
                  className="h-3.5 w-3.5 rounded-full shrink-0 flex items-center justify-center shadow-xs"
                  style={{ backgroundColor: accent.hex }}
                >
                  {isSelected && <Check className="h-2 w-2 text-white stroke-[3]" />}
                </span>
                <span className="truncate">{accent.name}</span>
              </button>
            );
          })}

          {/* Custom Accent Option */}
          <button
            type="button"
            onClick={() => {
              setAccentColor('custom');
              if (colorInputRef.current) {
                colorInputRef.current.click();
              }
            }}
            className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
              accentColor === 'custom'
                ? 'bg-slate-800/90 border-slate-600 text-white font-semibold shadow-sm'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
            }`}
          >
            <span
              className="h-3.5 w-3.5 rounded-full shrink-0 flex items-center justify-center shadow-xs border border-white/20"
              style={{ backgroundColor: activeCustomColor }}
            >
              {accentColor === 'custom' ? (
                <Check className="h-2 w-2 text-white stroke-[3]" />
              ) : (
                <Palette className="h-2 w-2 text-white" />
              )}
            </span>
            <span className="truncate">Custom</span>
          </button>
        </div>

        {/* Custom Color Picker Expanded Panel */}
        {accentColor === 'custom' && (
          <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl border border-slate-800 bg-slate-950/60 text-xs animate-in fade-in duration-150">
            <div className="flex items-center gap-2">
              <label htmlFor="custom-color-picker" className="text-slate-400">
                Choose Color:
              </label>
              <div className="relative flex items-center">
                <input
                  ref={colorInputRef}
                  id="custom-color-picker"
                  type="color"
                  value={activeCustomColor}
                  onChange={(e) => setCustomAccentColor(e.target.value)}
                  className="w-8 h-8 rounded-lg cursor-pointer border border-slate-700 bg-transparent p-0.5"
                  title="Choose custom color"
                />
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-mono">HEX:</span>
              <input
                type="text"
                value={activeCustomColor}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val.startsWith('#') && val.length <= 7) {
                    setCustomAccentColor(val);
                  } else if (!val.startsWith('#') && val.length <= 6) {
                    setCustomAccentColor('#' + val);
                  }
                }}
                maxLength={7}
                className="w-20 px-2 py-1 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs font-mono uppercase focus:outline-none focus:border-blue-500"
                placeholder="#2563EB"
              />
            </div>

            <span className="text-[11px] text-slate-400">
              Accessible variants are automatically derived.
            </span>
          </div>
        )}
      </div>

      {/* Typography Font */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold text-slate-300">Typography Font</label>
        <div className="grid grid-cols-3 gap-2.5">
          {FONTS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setFont(item.id)}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                font === item.id
                  ? 'bg-blue-600/10 border-blue-500 text-white font-semibold'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <div className="text-xs font-semibold text-slate-200">{item.label}</div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Text Size */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold text-slate-300">Text Size</label>
        <div className="grid grid-cols-3 gap-2.5">
          {TEXT_SIZES.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTextSize(item.id)}
              className={`p-2.5 rounded-xl border text-center text-xs font-medium transition-all cursor-pointer ${
                textSize === item.id
                  ? 'bg-blue-600/10 border-blue-500 text-white font-semibold'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <div>{item.label}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Interface & Behavior Toggles */}
      <div className="space-y-3 pt-2">
        {/* Enable UI Animations */}
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 shrink-0 mt-0.5">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Enable UI Animations</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Smooth transitions, modal animations, and interactive state movements.
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={animationsEnabled}
            onClick={() => setAnimationsEnabled(!animationsEnabled)}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              animationsEnabled ? 'bg-blue-600' : 'bg-slate-800'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                animationsEnabled ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Reduce Motion */}
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 shrink-0 mt-0.5">
              <EyeOff className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Reduce Motion</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Suppress non-essential decorative animations and movement for accessibility.
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={reduceMotion}
            onClick={() => setReduceMotion(!reduceMotion)}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              reduceMotion ? 'bg-blue-600' : 'bg-slate-800'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                reduceMotion ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Remember Last Opened Section */}
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 shrink-0 mt-0.5">
              <Bookmark className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Remember Last Opened Section</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Reopen the settings modal to the last tab you visited instead of always opening General.
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={rememberLastSection}
            onClick={() => setRememberLastSection(!rememberLastSection)}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              rememberLastSection ? 'bg-blue-600' : 'bg-slate-800'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                rememberLastSection ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Reset Appearance */}
      <div className="pt-4 border-t border-slate-800/80 space-y-2">
        <div>
          <h3 className="text-xs font-semibold text-slate-200">Reset Appearance</h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Restore all appearance and interface preferences to their defaults.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsResetDialogOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-800 bg-slate-950/60 hover:bg-slate-900 text-slate-300 hover:text-white text-xs font-medium transition-colors cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Reset to defaults</span>
        </button>
      </div>

      <ResetAppearanceDialog
        isOpen={isResetDialogOpen}
        onClose={() => setIsResetDialogOpen(false)}
        onConfirm={handleConfirmReset}
      />
    </div>
  );
}
