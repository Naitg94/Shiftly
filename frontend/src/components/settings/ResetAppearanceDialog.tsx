'use client';

import { useEffect, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { RotateCcw, X } from 'lucide-react';

interface ResetAppearanceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const emptySubscribe = () => () => {};

export default function ResetAppearanceDialog({
  isOpen,
  onClose,
  onConfirm,
}: ResetAppearanceDialogProps) {
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reset-dialog-title"
        className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-5 sm:p-6 text-left space-y-4 animate-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <RotateCcw className="h-4 w-4" />
            </div>
            <h3 id="reset-dialog-title" className="text-base font-bold text-white tracking-tight">
              Reset appearance?
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Description */}
        <p className="text-xs text-slate-300 leading-relaxed">
          This will restore all appearance and interface preferences to their default values. Account, projects, and analysis data will not be affected.
        </p>

        {/* Defaults Summary Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span>Theme</span>
            <span className="font-semibold text-slate-200">Light</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Accent</span>
            <span className="font-semibold text-slate-200">Blue</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Font</span>
            <span className="font-semibold text-slate-200">Default (Geist)</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Text size</span>
            <span className="font-semibold text-slate-200">Default (16px)</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>UI animations</span>
            <span className="font-semibold text-slate-200">Enabled</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Reduce motion</span>
            <span className="font-semibold text-slate-200">Disabled</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Remember section</span>
            <span className="font-semibold text-slate-200">Enabled</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800/80">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-all shadow-md shadow-blue-500/20 cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset appearance</span>
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
