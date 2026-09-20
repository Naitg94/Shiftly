'use client';

import { useState, useEffect } from 'react';
import { BarChart3, CheckCircle2, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { getAccountSummary, AccountSummaryResponse, ApiError } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import SettingsPlanBadge from './SettingsPlanBadge';

export default function UsageSettings() {
  const { currentPlan } = useAuth();
  const [data, setData] = useState<AccountSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function loadSummary() {
      try {
        const res = await getAccountSummary();
        if (mounted) {
          setData(res);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (mounted) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else if (err instanceof Error) {
            setError(err.message);
          } else {
            setError('Failed to load usage statistics.');
          }
          setIsLoading(false);
        }
      }
    }
    loadSummary();
    return () => {
      mounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-3">
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        <span className="text-xs text-slate-400">Loading usage metrics...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5">
        <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
        <span>{error || 'Unable to display usage metrics at this time.'}</span>
      </div>
    );
  }

  const { usage } = data;

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header with Plan Badge */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">Usage</h2>
          <p className="text-xs text-slate-400 mt-0.5">Track resource consumption across your Shiftly account.</p>
        </div>
        <SettingsPlanBadge plan={data?.plan?.id || currentPlan} />
      </div>

      {/* Resource Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        {/* Analyses Metric */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Analyses Conducted</span>
            <span className="text-xs font-mono font-bold text-white">
              {usage.analyses_count}
              <span className="text-slate-500 font-normal">
                {usage.analyses_limit ? ` / ${usage.analyses_limit}` : ' / Unlimited'}
              </span>
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  Math.max(5, (usage.analyses_count / (usage.analyses_limit || 100)) * 100)
                )}%`,
              }}
            />
          </div>
          <p className="text-[11px] text-slate-400">
            {usage.analyses_limit
              ? `Monthly analysis limit: ${usage.analyses_limit} per calendar month.`
              : 'Unlimited monthly analyses.'}
          </p>
        </div>

        {/* Projects Metric */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Active Projects</span>
            <span className="text-xs font-mono font-bold text-white">
              {usage.projects_count}
              <span className="text-slate-500 font-normal">
                {usage.projects_limit ? ` / ${usage.projects_limit}` : ' / Unlimited'}
              </span>
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  Math.max(5, (usage.projects_count / (usage.projects_limit || 50)) * 100)
                )}%`,
              }}
            />
          </div>
          <p className="text-[11px] text-slate-400">
            Persistent Project Memory workspaces for your communication data.
          </p>
        </div>
      </div>

      {/* Characters Processed */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-xs font-semibold text-slate-300">Characters Extracted</span>
            <p className="text-[11px] text-slate-400">
              Total communication intelligence characters stored in memory.
            </p>
          </div>
          <span className="text-xs font-mono font-bold text-white">
            {usage.characters_processed.toLocaleString()} chars
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400 pt-1 border-t border-slate-800/80">
          <Sparkles className="h-3.5 w-3.5 text-blue-400 shrink-0" />
          <span>Per-analysis processing limit: <strong>{usage.characters_limit.toLocaleString()} characters</strong></span>
        </div>
      </div>

      {/* Supported Inputs Grid */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold text-slate-300">Supported Communication Inputs</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {usage.supported_inputs.map((input) => (
            <div
              key={input.name}
              className={`flex items-center justify-between p-2.5 rounded-xl border text-xs ${
                input.supported
                  ? 'border-slate-800 bg-slate-950/40 text-slate-200'
                  : 'border-slate-800/40 bg-slate-950/20 text-slate-500'
              }`}
            >
              <span className="font-semibold">{input.name}</span>
              {input.supported ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Locked</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
