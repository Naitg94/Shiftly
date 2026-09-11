'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Sparkles, Loader2, AlertCircle, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { signIn, user, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && user) {
      router.replace('/');
    }
  }, [user, isLoading, router]);

  if (isLoading || user) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-xl shadow-lg shadow-blue-500/20">
          S
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          <span>{user ? 'Redirecting to Shiftly...' : 'Checking session...'}</span>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const { error } = await signIn(email.trim(), password);
      if (error) {
        setErrorMessage(error.message);
      } else {
        router.replace('/');
      }
    } catch {
      setErrorMessage('An unexpected error occurred during sign-in.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12 selection:bg-blue-600 selection:text-white">
      {/* Brand Header */}
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="inline-flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-xl shadow-lg shadow-blue-500/20">
            S
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">Shiftly</span>
        </div>
        <div className="space-y-1">
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Sign in to Shiftly
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Communication intelligence layer for your projects.
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 shadow-2xl text-left space-y-5">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Email Address
              </label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">
                  Password
                </label>
              </div>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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
                  <span>Sign In</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/80">
            Don&apos;t have an account?{' '}
            <Link
              href="/signup"
              className="text-blue-400 hover:text-blue-300 font-medium hover:underline transition-colors"
            >
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
