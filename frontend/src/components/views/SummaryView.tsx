"use client";

import { ShiftlyAnalysisResult } from "@/types/analysis";
import { FileText, CheckCircle2, Clock } from "lucide-react";

interface SummaryViewProps {
  result: ShiftlyAnalysisResult;
}

export default function SummaryView({ result }: SummaryViewProps) {
  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Executive Summary
        </h3>
        <span className="text-xs text-slate-500">Condensed from {result.stats.messagesAnalyzed} messages</span>
      </div>

      {/* Main Paragraph */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8 space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
          <FileText className="h-4 w-4" />
          <span>Synthesis</span>
        </div>
        <p className="text-base sm:text-lg text-slate-200 leading-relaxed font-normal">
          {result.summary}
        </p>
      </div>

      {/* Highlights Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            <span>Primary Resolution</span>
          </div>
          <p className="text-xs text-slate-300">
            Triple-pane glazing upgrade approved (+ $14.2k) preserving November 3 delivery schedule.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium text-amber-400">
            <Clock className="h-4 w-4" />
            <span>Immediate Milestone</span>
          </div>
          <p className="text-xs text-slate-300">
            Rebar inspection report sign-off required by Oct 14 noon to enable Oct 15 slab pour.
          </p>
        </div>
      </div>
    </div>
  );
}
