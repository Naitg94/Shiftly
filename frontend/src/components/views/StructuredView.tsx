"use client";

import { ShiftlyAnalysisResult, SourceReference } from "@/types/analysis";
import { CheckSquare, Gavel, Calendar, Key, Info, User, Clock } from "lucide-react";

interface StructuredViewProps {
  result: ShiftlyAnalysisResult;
  onOpenSource: (source: SourceReference) => void;
}

export default function StructuredView({ result, onOpenSource }: StructuredViewProps) {
  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Actions Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
              <CheckSquare className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Action Items ({result.actions.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Owner & target deadlines</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {result.actions.map((act) => (
            <div
              key={act.id}
              className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-slate-100 leading-snug">
                    {act.action}
                  </p>
                  <button
                    onClick={() => onOpenSource(act.source)}
                    className="shrink-0 p-1 text-slate-500 hover:text-blue-400 rounded transition-colors"
                    title="View source citation"
                    aria-label={`View source citation for action: ${act.action.slice(0, 30)}`}
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                <div className="flex items-center gap-1.5 truncate">
                  <User className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                  <span className="truncate">{act.responsiblePerson}</span>
                </div>
                {act.deadline && (
                  <div className="flex items-center gap-1 text-amber-300 font-mono text-[11px] bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    <Clock className="h-3 w-3" />
                    <span>{act.deadline}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 2. Decisions Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
              <Gavel className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Decisions & Approvals ({result.decisions.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Sign-offs & confirmations</span>
        </div>

        <div className="space-y-3">
          {result.decisions.map((dec) => (
            <div
              key={dec.id}
              className="flex items-start justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 transition-colors"
            >
              <div className="space-y-1.5">
                <p className="text-sm text-slate-100 font-medium leading-relaxed">
                  {dec.decision}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-1 text-emerald-400">
                    Approved by: <strong className="font-semibold text-slate-200">{dec.approvedBy}</strong>
                  </span>
                  {dec.date && (
                    <>
                      <span>&bull;</span>
                      <span className="text-slate-500 font-mono">{dec.date}</span>
                    </>
                  )}
                </div>
              </div>

              <button
                onClick={() => onOpenSource(dec.source)}
                className="shrink-0 inline-flex items-center gap-1 rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-400 hover:text-blue-300 hover:border-blue-500/40 transition-colors"
                title="View source citation"
                aria-label={`View source citation for decision: ${dec.decision.slice(0, 30)}`}
              >
                <Info className="h-3.5 w-3.5 text-blue-400" />
                <span className="hidden sm:inline text-[11px]">Source</span>
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Important Dates Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-purple-500/10 flex items-center justify-center text-purple-400 border border-purple-500/20">
              <Calendar className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Important Dates & Milestones ({result.importantDates.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Key project milestones</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {result.importantDates.map((dt) => (
            <div
              key={dt.id}
              className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-sm text-purple-300 font-mono">
                    {dt.date}
                  </div>
                  <button
                    onClick={() => onOpenSource(dt.source)}
                    className="p-1 text-slate-500 hover:text-blue-400 rounded transition-colors"
                    title="View source citation"
                    aria-label={`View source citation for date: ${dt.title}`}
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </div>
                <h4 className="text-sm font-medium text-slate-200 mt-1">{dt.title}</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{dt.significance}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Key Points Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
              <Key className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Key Points & Context ({result.keyPoints.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Core discussion topics</span>
        </div>

        <ul className="space-y-2.5">
          {result.keyPoints.map((kp) => (
            <li
              key={kp.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-slate-800/80 bg-slate-900/30 p-3 hover:bg-slate-900/60 transition-colors"
            >
              <div className="flex items-start gap-2.5">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 mt-2 shrink-0"></span>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">{kp.point}</p>
              </div>
              <button
                onClick={() => onOpenSource(kp.source)}
                className="shrink-0 p-1 text-slate-500 hover:text-blue-400 rounded transition-colors"
                title="View source citation"
                aria-label={`View source citation for key point: ${kp.point.slice(0, 30)}`}
              >
                <Info className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
