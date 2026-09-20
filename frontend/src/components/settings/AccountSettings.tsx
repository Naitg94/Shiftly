'use client';

import { useState } from 'react';
import Link from 'next/link';
import { User, Mail, Key, ShieldAlert, Copy, Check, Loader2, LogOut, CheckCircle2, Lock } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import SettingsPlanBadge from './SettingsPlanBadge';
import DeleteAccountDialog from './DeleteAccountDialog';

interface AccountSettingsProps {
  onSignOut: () => Promise<void>;
}

export default function AccountSettings({ onSignOut }: AccountSettingsProps) {
  const { user, username, updateUsername, currentPlan } = useAuth();

  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [newUsername, setNewUsername] = useState(username || '');
  const [isSavingUsername, setIsSavingUsername] = useState(false);
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [usernameSuccess, setUsernameSuccess] = useState<string | null>(null);

  const [isCopiedId, setIsCopiedId] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  if (!user) return null;

  const handleCopyUserId = async () => {
    try {
      await navigator.clipboard.writeText(user.id);
      setIsCopiedId(true);
      setTimeout(() => setIsCopiedId(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSaveUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newUsername.trim();
    if (!trimmed) {
      setUsernameError('Username cannot be empty.');
      return;
    }
    if (trimmed.length < 2) {
      setUsernameError('Username must be at least 2 characters long.');
      return;
    }
    if (trimmed.length > 50) {
      setUsernameError('Username cannot exceed 50 characters.');
      return;
    }
    if (/[\u0000-\u001F\u007F-\u009F]/.test(trimmed)) {
      setUsernameError('Username contains invalid characters.');
      return;
    }

    setIsSavingUsername(true);
    setUsernameError(null);
    setUsernameSuccess(null);

    const { error } = await updateUsername(trimmed);
    setIsSavingUsername(false);

    if (error) {
      setUsernameError(error.message);
    } else {
      setUsernameSuccess('Username updated successfully!');
      setTimeout(() => {
        setIsEditingUsername(false);
        setUsernameSuccess(null);
      }, 1500);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header with Plan Badge */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">Account</h2>
          <p className="text-xs text-slate-400 mt-0.5">Manage your identity and authentication credentials.</p>
        </div>
        <SettingsPlanBadge plan={currentPlan} />
      </div>

      {/* Account Info Cards */}
      <div className="space-y-3.5">
        {/* Username */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <User className="h-3.5 w-3.5 text-blue-400" />
              <span>Username</span>
            </div>
            {!isEditingUsername && (
              <button
                type="button"
                onClick={() => {
                  setNewUsername(username);
                  setUsernameError(null);
                  setIsEditingUsername(true);
                }}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium hover:underline transition-colors cursor-pointer"
              >
                Edit
              </button>
            )}
          </div>

          {isEditingUsername ? (
            <form onSubmit={handleSaveUsername} className="space-y-2 pt-1">
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                maxLength={50}
                placeholder="Enter username"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
              {usernameError && <p className="text-[11px] text-rose-400">{usernameError}</p>}
              {usernameSuccess && <p className="text-[11px] text-emerald-400">{usernameSuccess}</p>}
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditingUsername(false);
                    setUsernameError(null);
                  }}
                  className="px-2.5 py-1 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingUsername}
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {isSavingUsername && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span>Save</span>
                </button>
              </div>
            </form>
          ) : (
            <div className="text-xs font-mono font-medium text-white">
              {username || user.email?.split('@')[0]}
            </div>
          )}
        </div>

        {/* Email */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Mail className="h-3.5 w-3.5 text-blue-400" />
              <span>Email Address</span>
            </div>
            {Boolean(user.email_confirmed_at || user.user_metadata?.email_verified) ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" />
                Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                Unverified
              </span>
            )}
          </div>
          <div className="text-xs font-mono text-slate-300 select-all">
            {user.email}
          </div>
        </div>

        {/* User ID */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Key className="h-3.5 w-3.5 text-blue-400" />
              <span>User ID</span>
            </div>
            <button
              type="button"
              onClick={handleCopyUserId}
              className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium hover:underline transition-colors cursor-pointer"
            >
              {isCopiedId ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <div className="text-xs font-mono text-slate-400 select-all truncate">
            {user.id}
          </div>
        </div>

        {/* Password & Security */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Lock className="h-3.5 w-3.5 text-slate-400" />
              <div className="text-xs font-semibold text-slate-200">Password &amp; Security</div>
            </div>
            <p className="text-[11px] text-slate-400">Manage your password and account recovery.</p>
            <div className="flex items-center gap-2 pt-0.5 text-[11px] text-slate-400">
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-300 text-[10px] font-medium">
                Email &amp; Password
              </span>
              <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                <Check className="h-3 w-3" /> Password protected
              </span>
            </div>
          </div>
          <Link
            href="/forgot-password"
            className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 hover:text-white text-slate-200 text-xs font-medium transition-colors cursor-pointer shrink-0"
          >
            Forgot Password
          </Link>
        </div>
      </div>

      {/* Sign Out Action */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onSignOut}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-900 text-slate-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>Sign Out of Shiftly</span>
        </button>
      </div>

      {/* Danger Zone */}
      <div className="rounded-2xl border border-rose-900/40 bg-rose-950/10 p-5 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400">
          <ShieldAlert className="h-4 w-4" />
          <span>Danger Zone</span>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="text-xs font-semibold text-white">Delete Account</div>
            <p className="text-[11px] text-slate-400">
              Permanently delete your Shiftly account and associated Project Memory.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsDeleteDialogOpen(true)}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/30 hover:border-rose-600 transition-all cursor-pointer shrink-0"
          >
            Delete Account
          </button>
        </div>
      </div>

      {/* Confirmation Dialog */}
      <DeleteAccountDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => setIsDeleteDialogOpen(false)}
        onSuccess={async () => {
          setIsDeleteDialogOpen(false);
          await onSignOut();
        }}
      />
    </div>
  );
}
