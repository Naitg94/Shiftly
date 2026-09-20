'use client';

import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { useAuth } from '@/context/AuthContext';
import { PLANS } from '@/config/plans';
import {
  Check,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Layers,
  Zap,
  Clock,
  Building,
} from 'lucide-react';

export default function PlansPage() {
  const { user, currentPlan } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Navbar with active plan badge */}
      <Navbar />

      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 flex flex-col justify-start space-y-10">
        {/* Header Banner */}
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-600/10 text-xs font-semibold text-blue-400">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Subscription & Plans</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-white">
            Simple, transparent tiers
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            Shiftly is currently free during preview.
          </p>
        </div>

        {/* Current Usage & Status Card (NO fake progress bars or counters) */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                currentPlan === 'PRO'
                  ? 'bg-cyan-600/20 border border-cyan-500/30 text-cyan-400'
                  : user
                  ? 'bg-blue-600/20 border border-blue-500/30 text-blue-400'
                  : 'bg-slate-800 border border-slate-700 text-slate-400'
              }`}>
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-white">Account Status</h2>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      currentPlan === 'PRO'
                        ? 'border-cyan-500/30 bg-cyan-600/10 text-cyan-400'
                        : user
                        ? 'border-blue-500/30 bg-blue-600/10 text-blue-400'
                        : 'border-slate-700 bg-slate-800 text-slate-300'
                    }`}
                  >
                    {currentPlan === 'PRO'
                      ? 'PRO PLAN — ACTIVE'
                      : user
                      ? 'FREE PLAN — ACTIVE'
                      : 'GUEST ACCESS'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {currentPlan === 'PRO'
                    ? 'Authenticated account with unlimited Pro capabilities.'
                    : user
                    ? 'Authenticated account with essential Project Memory capabilities.'
                    : 'Ad-hoc analysis without an account.'}
                </p>
              </div>
            </div>

            {/* Quick Action CTA for Guests */}
            {!user && (
              <div className="flex flex-wrap items-center gap-2 pt-1 sm:pt-0">
                <Link
                  href="/login"
                  className="px-3.5 py-1.5 rounded-xl border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
                >
                  Log In
                </Link>
                <Link
                  href="/signup"
                  className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-sm shadow-blue-500/20 transition-all"
                >
                  Sign Up Free
                </Link>
              </div>
            )}
          </div>

          {/* Clean Usage Explanation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-slate-300 font-semibold">
                <Zap className={`h-4 w-4 ${currentPlan === 'PRO' ? 'text-cyan-400' : 'text-blue-400'}`} />
                <span>AI Usage & Monthly Quota</span>
              </div>
              <p className="text-slate-400 leading-relaxed">
                {currentPlan === 'PRO' ? (
                  <span className="text-slate-300 font-medium">
                    Pro plan includes unlimited monthly analyses and 50 Project Memory workspaces.
                  </span>
                ) : user ? (
                  <span className="text-slate-300 font-medium">
                    Free plan includes 30 analyses per calendar month and 10 Project Memory workspaces.
                  </span>
                ) : (
                  <span>
                    Guests can analyze ad-hoc communications up to 3,000 characters (pasted text) or 1,500 characters (uploaded file) per analysis.
                  </span>
                )}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-slate-300 font-semibold">
                <Layers className="h-4 w-4 text-slate-400" />
                <span>Technical Safeguards</span>
              </div>
              <p className="text-slate-400 leading-relaxed">
                {currentPlan === 'PRO' ? (
                  <span>
                    Up to 200,000 characters per analysis · 25 MB file size limit · 4 GB Project Memory storage.
                  </span>
                ) : user ? (
                  <span>
                    Up to 50,000 characters per analysis · 10 MB file size limit · 10 analyses/min abuse protection.
                  </span>
                ) : (
                  <span>
                    Create a free account to unlock 50,000 characters and persistent Project Memory.
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* 3 Tier Plans Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {PLANS.map((plan, planIdx) => {
            const isCurrent = user ? currentPlan === plan.id : false;
            const isPlusOrPro = plan.id === 'PLUS' || plan.id === 'PRO';
            const isLastOnTablet = planIdx === 2;

            const freeIncludedLabel = currentPlan === 'PRO' ? 'Included in Pro' : currentPlan === 'PLUS' ? 'Included in Plus' : 'Available';

            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl border p-6 sm:p-7 flex flex-col justify-between transition-all ${
                  isLastOnTablet ? 'md:col-span-2 md:w-full md:max-w-[360px] md:mx-auto lg:max-w-none lg:col-span-1' : ''
                } ${
                  isCurrent
                    ? plan.id === 'PRO'
                      ? 'border-cyan-500/40 bg-slate-900 shadow-xl shadow-cyan-500/5 ring-1 ring-cyan-500/20'
                      : plan.id === 'PLUS'
                      ? 'border-amber-500/40 bg-slate-900 shadow-xl shadow-amber-500/5 ring-1 ring-amber-500/20'
                      : 'border-blue-500/40 bg-slate-900 shadow-xl shadow-blue-500/5 ring-1 ring-blue-500/20'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700/80'
                }`}
              >
                {/* Badge Header */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold tracking-wider text-white">
                      {plan.name}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                        isCurrent
                          ? plan.id === 'PRO'
                            ? 'border-cyan-500/30 bg-cyan-600/10 text-cyan-400'
                            : plan.id === 'PLUS'
                            ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                            : 'border-blue-500/30 bg-blue-600/10 text-blue-400'
                          : plan.id === 'FREE' && user
                          ? 'border-slate-700 bg-slate-800 text-slate-400'
                          : isPlusOrPro
                          ? 'border-amber-500/20 bg-amber-500/10 text-amber-300'
                          : 'border-slate-700 bg-slate-800 text-slate-300'
                      }`}
                    >
                      {isCurrent
                        ? 'Current Plan'
                        : plan.id === 'FREE' && user
                        ? freeIncludedLabel
                        : isPlusOrPro
                        ? 'Coming Soon'
                        : 'Available'}
                    </span>
                  </div>

                  {/* Price & Tagline */}
                  <div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl sm:text-3xl font-extrabold text-white">
                        {plan.priceDisplay}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        / month
                      </span>
                    </div>
                    <p className={`text-xs font-medium mt-1 ${
                      isCurrent && plan.id === 'PRO'
                        ? 'text-cyan-400'
                        : isCurrent && plan.id === 'PLUS'
                        ? 'text-amber-400'
                        : 'text-blue-400'
                    }`}>
                      {plan.tagline}
                    </p>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-800/80 pt-3">
                    {plan.description}
                  </p>

                  {/* Feature Checklist */}
                  <div className="space-y-2.5 pt-2">
                    <p className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                      {plan.id === 'FREE' ? 'Included features:' : 'Plan capabilities:'}
                    </p>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {plan.features.map((feat, idx) => (
                        <li key={idx} className="flex items-start gap-2.5">
                          <Check className={`h-3.5 w-3.5 shrink-0 mt-0.5 ${
                            isCurrent && plan.id === 'PRO'
                              ? 'text-cyan-400'
                              : isCurrent && plan.id === 'PLUS'
                              ? 'text-amber-400'
                              : 'text-blue-400'
                          }`} />
                          <span className={!isCurrent && isPlusOrPro ? 'text-slate-400' : 'text-slate-200'}>
                            {feat}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Card Action Button */}
                <div className="pt-6 border-t border-slate-800/80 mt-6">
                  {isCurrent ? (
                    <div className={`w-full text-center py-2.5 rounded-xl border text-xs font-semibold cursor-default select-none ${
                      plan.id === 'PRO'
                        ? 'border-cyan-500/30 bg-cyan-600/10 text-cyan-400'
                        : plan.id === 'PLUS'
                        ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                        : 'border-blue-500/30 bg-blue-600/10 text-blue-400'
                    }`}>
                      Current Active Plan
                    </div>
                  ) : plan.id === 'FREE' && user ? (
                    <div className="w-full text-center py-2.5 rounded-xl border border-slate-800 bg-slate-950/60 text-xs font-medium text-slate-500 cursor-default select-none">
                      {freeIncludedLabel}
                    </div>
                  ) : isPlusOrPro ? (
                    <button
                      type="button"
                      disabled
                      aria-disabled="true"
                      className="w-full py-2.5 rounded-xl border border-slate-800 bg-slate-950/60 text-xs font-semibold text-slate-500 cursor-not-allowed select-none"
                    >
                      Coming Soon
                    </button>
                  ) : (
                    <Link
                      href="/signup"
                      className="w-full inline-flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-sm shadow-blue-500/20 transition-all cursor-pointer"
                    >
                      <span>Create Free Account</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Minimal Bottom Notice */}
        <div className="text-center text-xs text-slate-500 border-t border-slate-900 pt-6">
          <p>
            Shiftly is currently in active preview. All plans and future capacity tiers will be introduced with advance notice.
          </p>
        </div>
      </main>
    </div>
  );
}
