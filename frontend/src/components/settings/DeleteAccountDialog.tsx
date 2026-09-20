'use client';

import { useState, useEffect, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, Loader2, X } from 'lucide-react';
import { deleteAccount, ApiError } from '@/lib/api';

interface DeleteAccountDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => Promise<void>;
}

const emptySubscribe = () => () => {};

export default function DeleteAccountDialog({
  isOpen,
  onClose,
  onSuccess,
}: DeleteAccountDialogProps) {
  const [password, setPassword] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);

  if (!isOpen || !mounted) return null;

  const isPasswordEntered = password.trim().length > 0;

  const handleDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isPasswordEntered || isDeleting) return;

    setIsDeleting(true);
    setError(null);

    try {
      await deleteAccount(password);
      setPassword('');
      await onSuccess();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || 'Incorrect password. Please try again.');
      } else if (err instanceof Error) {
        setError(err.message || 'Incorrect password. Please try again.');
      } else {
        setError('Incorrect password. Please try again.');
      }
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    if (isDeleting) return;
    setPassword('');
    setError(null);
    onClose();
  };

  return createPortal(
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-md rounded-2xl border border-rose-900/40 bg-slate-900 shadow-2xl p-5 sm:p-6 text-left space-y-4 animate-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5 text-rose-400">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
              <AlertTriangle className="h-5 w-5 text-rose-400" />
            </div>
            <h3 className="text-base font-bold text-white">Delete your account?</h3>
          </div>
          <button
            onClick={handleClose}
            disabled={isDeleting}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
          <p>
            This permanently deletes your Shiftly account and associated{' '}
            <strong className="text-white font-semibold">Project Memory</strong>.
            This action cannot be undone.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleDelete} className="space-y-4 pt-1">
          <div className="space-y-1.5">
            <label htmlFor="delete-account-password-input" className="text-xs font-semibold text-slate-300">
              Current password
            </label>
            <input
              id="delete-account-password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isDeleting}
              placeholder="•••••••••••••••••••••••"
              autoComplete="current-password"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-rose-500 transition-colors"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={handleClose}
              disabled={isDeleting}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isPasswordEntered || isDeleting}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-sm shadow-rose-600/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Deleting Account...</span>
                </>
              ) : (
                <span>Delete Account</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
