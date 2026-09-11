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

      {/* Highlights Grid derived strictly from live results */}
      {(result.decisions.length > 0 || result.importantDates.length > 0 || result.actions.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {result.decisions.length > 0 && (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                <span>Primary Resolution</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {result.decisions[0].decision}
                {result.decisions[0].approvedBy && result.decisions[0].approvedBy !== "Unknown" && (
                  <span className="text-slate-500 ml-1.5">(Approved by {result.decisions[0].approvedBy})</span>
                )}
              </p>
            </div>
          )}

          {result.importantDates.length > 0 ? (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-medium text-amber-400">
                <Clock className="h-4 w-4" />
                <span>Key Milestone</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                <span className="font-mono text-amber-300 mr-1.5">{result.importantDates[0].date}</span>
                — {result.importantDates[0].title}
              </p>
            </div>
          ) : result.actions.length > 0 ? (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-medium text-amber-400">
                <Clock className="h-4 w-4" />
                <span>Immediate Action</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {result.actions[0].action}
                {result.actions[0].responsiblePerson && result.actions[0].responsiblePerson !== "Unassigned" && (
                  <span className="text-slate-500 ml-1.5">({result.actions[0].responsiblePerson})</span>
                )}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
