'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  KeyRound,
  ShieldAlert,
} from 'lucide-react';
import { verifyRecoveryAccount, resetRecoveryPassword, ApiError } from '@/lib/api';

type Step = 'verify' | 'reset' | 'success';

export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step, setStep] = useState<Step>('verify');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null);

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Step 1: Verify Username + Email
  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUser = username.trim();
    const cleanEmail = email.trim();

    if (!cleanUser || !cleanEmail) {
      setErrorMessage('Please fill in both your display name and email address.');
      return;
    }

    if (cleanUser.length < 2 || cleanUser.length > 50) {
      setErrorMessage('Display name must be between 2 and 50 characters.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const data = await verifyRecoveryAccount(cleanUser, cleanEmail);
      setRecoveryToken(data.recovery_token);
      setStep('reset');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Unable to verify account details. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 2: Reset Password with recovery token
  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!recoveryToken) {
      setErrorMessage('Recovery session missing. Please start over.');
      setStep('verify');
      return;
    }

    if (!newPassword || !confirmPassword) {
      setErrorMessage('Please enter and confirm your new password.');
      return;
    }

    if (newPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please re-enter your password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await resetRecoveryPassword(recoveryToken, newPassword, confirmPassword);
      setRecoveryToken(null);
      setStep('success');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to reset password. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12 selection:bg-blue-600 selection:text-white">
      <div className="w-full max-w-md space-y-6 text-center">
        {/* Brand Header */}
        <div className="inline-flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-xl shadow-lg shadow-blue-500/20">
            S
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">Shiftly</span>
        </div>

        <div className="space-y-1">
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Account Recovery
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            {step === 'verify' && 'Verify your account using your username and email.'}
            {step === 'reset' && 'Create a new secure password for your account.'}
            {step === 'success' && 'Your account password has been updated.'}
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-8 shadow-2xl text-left space-y-5">
          {/* MVP Recovery Notice Banner */}
          {step !== 'success' && (
            <div className="p-3.5 rounded-xl bg-blue-600/10 border border-blue-500/20 text-xs text-blue-300 flex items-start gap-2.5">
              <KeyRound className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold text-white">MVP Account Recovery</p>
                <p className="text-blue-300/90 leading-relaxed">
                  For this MVP, account recovery uses your username and email address.
                </p>
              </div>
            </div>
          )}

          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5 animate-in fade-in duration-150">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* STEP 1: Verify Username + Email */}
          {step === 'verify' && (
            <form onSubmit={handleVerifySubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="recovery-username" className="text-xs font-semibold text-slate-300">
                  Username / Display Name
                </label>
                <input
                  id="recovery-username"
                  type="text"
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  maxLength={50}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="recovery-email" className="text-xs font-semibold text-slate-300">
                  Email Address
                </label>
                <input
                  id="recovery-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 py-2.5 text-sm font-semibold text-white transition-all shadow-md shadow-blue-600/20 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <span>Verify Account</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* STEP 2: Choose New Password */}
          {step === 'reset' && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="recovery-new-password" className="text-xs font-semibold text-slate-300">
                  New Password
                </label>
                <input
                  id="recovery-new-password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  minLength={8}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="recovery-confirm-password" className="text-xs font-semibold text-slate-300">
                  Confirm New Password
                </label>
                <input
                  id="recovery-confirm-password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your new password"
                  minLength={8}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 py-2.5 text-sm font-semibold text-white transition-all shadow-md shadow-blue-600/20 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <span>Reset Password</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep('verify');
                  setRecoveryToken(null);
                  setErrorMessage(null);
                }}
                className="w-full text-center text-xs text-slate-400 hover:text-slate-300 py-1 transition-colors cursor-pointer"
              >
                Back to verification
              </button>
            </form>
          )}

          {/* STEP 3: Success Screen */}
          {step === 'success' && (
            <div className="text-center py-4 space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">Password Updated</h3>
                <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
                  Your password has been reset successfully. You can now sign in using your new password.
                </p>
              </div>

              <Link
                href="/login"
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 py-2.5 text-sm font-semibold text-white transition-all shadow-md shadow-blue-600/20 cursor-pointer"
              >
                <span>Return to Log In</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}

          {step !== 'success' && (
            <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/80">
              Remember your password?{' '}
              <Link
                href="/login"
                className="text-blue-400 hover:text-blue-300 font-medium hover:underline transition-colors cursor-pointer"
              >
                Sign in
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
