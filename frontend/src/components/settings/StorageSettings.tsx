'use client';

import { useState, useEffect } from 'react';
import { HardDrive, CheckCircle2, ShieldCheck, Loader2, AlertCircle, Database } from 'lucide-react';
import { getAccountSummary, AccountSummaryResponse, ApiError } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import SettingsPlanBadge from './SettingsPlanBadge';

export default function StorageSettings() {
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
            setError('Failed to load storage details.');
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
        <span className="text-xs text-slate-400">Loading storage breakdown...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5">
        <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
        <span>{error || 'Unable to display storage breakdown at this time.'}</span>
      </div>
    );
  }

  const { storage } = data;
  const usedMB = (storage.used_bytes / (1024 * 1024)).toFixed(2);
  const formatLimit = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      const gb = bytes / (1024 * 1024 * 1024);
      return `${Number.isInteger(gb) ? gb : gb.toFixed(1)} GB`;
    }
    return `${Math.round(bytes / (1024 * 1024))} MB`;
  };
  const usagePercent = Math.min(100, Math.max(1, (storage.used_bytes / storage.limit_bytes) * 100));

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header with Plan Badge */}
      <div className="flex items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">Storage</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Shiftly persists extracted Project Intelligence, not raw conversation files.
          </p>
        </div>
        <SettingsPlanBadge plan={data?.plan?.id || currentPlan} />
      </div>

      {/* Storage Progress Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Database className="h-4 w-4" />
            </div>
            <span className="text-xs font-semibold text-slate-200">Project Memory Storage</span>
          </div>
          <span className="text-xs font-mono font-bold text-white">
            {usedMB} MB <span className="text-slate-500 font-normal">/ {formatLimit(storage.limit_bytes)}</span>
          </span>
        </div>

        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-sky-400 rounded-full transition-all duration-300"
            style={{ width: `${usagePercent}%` }}
          />
        </div>

        <p className="text-[11px] text-slate-400">
          Structured intelligence extracted from your team communications.
        </p>
      </div>

      {/* Entity Counters Breakdown */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold text-slate-300">Stored Project Intelligence</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {[
            { label: 'Projects', count: storage.projects_count },
            { label: 'Analyses', count: storage.analyses_count },
            { label: 'Key Points', count: storage.key_points_count },
            { label: 'Action Items', count: storage.action_items_count },
            { label: 'Decisions', count: storage.decisions_count },
            { label: 'Important Dates', count: storage.important_dates_count },
          ].map((item) => (
            <div
              key={item.label}
              className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 space-y-1"
            >
              <div className="text-[11px] text-slate-400 font-medium">{item.label}</div>
              <div className="text-sm font-bold font-mono text-white">{item.count}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Privacy / Product Concept Explanation */}
      <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2.5">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>What Shiftly Stores</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs text-slate-300">
          {storage.explanation.stored.map((item) => (
            <div key={item} className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
              <span>{item}</span>
            </div>
          ))}
        </div>

        <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/60 leading-relaxed">
          {storage.explanation.not_stored}
        </p>
      </div>
    </div>
  );
}
