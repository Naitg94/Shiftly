'use client';

import { Sparkles, CreditCard, FileText, Settings, Clock } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import SettingsPlanBadge from './SettingsPlanBadge';

export default function BillingSettings() {
  const { currentPlan } = useAuth();

  const isPro = currentPlan === 'PRO';
  const isPlus = currentPlan === 'PLUS';

  const planTitle = isPro ? 'Pro Plan' : isPlus ? 'Plus Plan' : 'Free Plan';
  const planPrice = isPro ? '$5' : isPlus ? '$1' : '$0';
  const planDescription = isPro
    ? 'Maximum capacity, unlimited analyses, and 4 GB Project Memory storage.'
    : isPlus
    ? 'Higher capacity, 150 analyses per month, and 1 GB Project Memory storage.'
    : 'Essential communication intelligence and Project Memory workspaces.';

  const cardBorderClass = isPro
    ? 'border-cyan-500/30 bg-cyan-600/5'
    : isPlus
    ? 'border-amber-500/30 bg-amber-600/5'
    : 'border-blue-500/30 bg-blue-600/5';

  const accentTextClass = isPro
    ? 'text-cyan-400'
    : isPlus
    ? 'text-amber-400'
    : 'text-blue-400';

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header with Plan Badge */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">Billing</h2>
          <p className="text-xs text-slate-400 mt-0.5">Manage your plan and future billing details.</p>
        </div>
        <SettingsPlanBadge plan={currentPlan} />
      </div>

      {/* Current Plan Card */}
      <div className={`rounded-2xl border p-5 space-y-4 ${cardBorderClass}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-white">{planTitle}</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {planDescription}
            </p>
          </div>
          <div className="text-right shrink-0">
            <span className="text-xl font-extrabold text-white">{planPrice}</span>
            <span className="text-xs text-slate-400 font-medium"> / month</span>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs">
          <div className={`flex items-center gap-1.5 ${accentTextClass}`}>
            <Sparkles className="h-3.5 w-3.5" />
            <span>{isPro ? 'Pro capabilities active' : isPlus ? 'Plus capabilities active' : 'Free plan active'}</span>
          </div>
          <Link
            href="/plans"
            className={`text-xs hover:underline transition-colors font-medium ${accentTextClass}`}
          >
            View plan overview &rarr;
          </Link>
        </div>
      </div>

      {/* Coming Soon Sections */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-300">Future Billing Features</h3>

        {/* Payment Methods */}
        <div className="flex items-start justify-between p-4 rounded-xl border border-slate-800/80 bg-slate-950/40">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-400 shrink-0 mt-0.5">
              <CreditCard className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Payment Methods</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Credit card, debit card, and digital payment methods will be available when paid tiers launch.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
            <Clock className="h-3 w-3" />
            Coming Soon
          </span>
        </div>

        {/* Invoices */}
        <div className="flex items-start justify-between p-4 rounded-xl border border-slate-800/80 bg-slate-950/40">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-400 shrink-0 mt-0.5">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Invoices & Receipts</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Downloadable PDF billing statements, VAT invoices, and transaction history.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
            <Clock className="h-3 w-3" />
            Coming Soon
          </span>
        </div>

        {/* Subscription Management */}
        <div className="flex items-start justify-between p-4 rounded-xl border border-slate-800/80 bg-slate-950/40">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-400 shrink-0 mt-0.5">
              <Settings className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Subscription Management</div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Seamless self-service upgrade, downgrade, or cancellation options.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
            <Clock className="h-3 w-3" />
            Coming Soon
          </span>
        </div>
      </div>
    </div>
  );
}
