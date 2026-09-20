"use client";

import { useMemo } from "react";
import { ShiftlyAnalysisResult, SourceReference, DecisionItem } from "@/types/analysis";
import {
  CheckSquare,
  Gavel,
  Calendar,
  Sparkles,
  Info,
  User,
  Clock,
  CheckCircle2,
  FileText,
  ShieldCheck,
} from "lucide-react";

interface StructuredViewProps {
  result: ShiftlyAnalysisResult;
  onOpenSource: (source: SourceReference) => void;
}

function isApprovalItem(item: DecisionItem): boolean {
  const hasExplicitApprover = Boolean(
    item.approvedBy && !["Unknown", "—", "Unassigned", "None", ""].includes(item.approvedBy.trim())
  );
  const textLower = item.decision.toLowerCase();
  const hasApprovalKeywords =
    textLower.includes("approv") ||
    textLower.includes("sign-off") ||
    textLower.includes("signed off") ||
    textLower.includes("authoriz");
  return hasExplicitApprover || hasApprovalKeywords;
}

export default function StructuredView({ result, onOpenSource }: StructuredViewProps) {
  const { decisions, approvals } = useMemo(() => {
    const decs: DecisionItem[] = [];
    const apps: DecisionItem[] = [];

    result.decisions.forEach((item) => {
      if (isApprovalItem(item)) {
        apps.push(item);
      } else {
        decs.push(item);
      }
    });

    return { decisions: decs, approvals: apps };
  }, [result.decisions]);

  return (
    <div className="space-y-10 animate-in fade-in duration-200">
      {/* 1. Analysis Summary */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
              <FileText className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Analysis Summary
            </h3>
          </div>
          <span className="text-xs text-slate-500">Executive Context</span>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 sm:p-6 space-y-2">
          <p className="text-sm sm:text-base text-slate-200 leading-relaxed font-normal">
            {result.summary || "No executive summary available."}
          </p>
        </div>
      </section>

      {/* 2. Key Points */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Key Points ({result.keyPoints.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Essential Takeaways</span>
        </div>

        {result.keyPoints.length === 0 ? (
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
            No key points were identified.
          </div>
        ) : (
          <ul className="space-y-2.5">
            {result.keyPoints.map((kp, idx) => (
              <li
                key={kp.id}
                className="flex items-start justify-between gap-3.5 rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start gap-3 flex-1">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-[11px] font-semibold text-blue-400 border border-blue-500/20 mt-0.5">
                    {idx + 1}
                  </span>
                  <div className="space-y-1 flex-1">
                    <p className="text-sm text-slate-200 leading-relaxed">{kp.point}</p>
                    {kp.category && (
                      <span className="inline-block text-[10px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700/60">
                        {kp.category}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => onOpenSource(kp.source)}
                  className="shrink-0 inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400 hover:border-blue-500/40 hover:text-blue-300 hover:bg-slate-900 transition-colors cursor-pointer"
                  title="View source citation"
                  aria-label={`View source citation for key point ${idx + 1}`}
                >
                  <Info className="h-3.5 w-3.5 text-blue-400" />
                  <span className="hidden sm:inline text-[11px]">Source</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 3. Action Items */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
              <CheckSquare className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Action Items ({result.actions.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">What &bull; Who &bull; When</span>
        </div>

        {result.actions.length === 0 ? (
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
            No explicit tasks or commitments were identified.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {result.actions.map((act) => {
              const hasOwner = act.responsiblePerson && !["Unassigned", "Unknown", "None", ""].includes(act.responsiblePerson.trim());
              const hasDeadline = Boolean(act.deadline && act.deadline.trim());

              return (
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
                        className="shrink-0 p-1 text-slate-500 hover:text-blue-400 rounded transition-colors cursor-pointer"
                        title="View source citation"
                        aria-label={`View source citation for action: ${act.action.slice(0, 30)}`}
                      >
                        <Info className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="pt-2.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                    <div className="flex items-center gap-1.5 truncate">
                      <User className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                      <span className={`truncate font-medium ${hasOwner ? "text-slate-200" : "text-slate-500 italic"}`}>
                        {hasOwner ? act.responsiblePerson : "Unassigned"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3 w-3 text-slate-500 shrink-0" />
                      {hasDeadline ? (
                        <span className="text-amber-300 font-mono text-[11px] bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          Due {act.deadline}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic text-[11px]">
                          No deadline specified
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 4. Important Dates */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-purple-500/10 flex items-center justify-center text-purple-400 border border-purple-500/20">
              <Calendar className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Important Dates ({result.importantDates.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Project Milestones</span>
        </div>

        {result.importantDates.length === 0 ? (
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
            No project-critical dates were identified.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {result.importantDates.map((dt) => (
              <div
                key={dt.id}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2 flex flex-col justify-between hover:border-slate-700 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 font-mono text-xs font-semibold uppercase tracking-wide">
                      <Calendar className="h-3 w-3" />
                      <span>{dt.date}</span>
                    </div>
                    <button
                      onClick={() => onOpenSource(dt.source)}
                      className="p-1 text-slate-500 hover:text-blue-400 rounded transition-colors cursor-pointer"
                      title="View source citation"
                      aria-label={`View source citation for date: ${dt.title}`}
                    >
                      <Info className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-100 mt-2.5">{dt.title}</h4>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{dt.significance}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 5. Decisions */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-indigo-500/10 flex items-center justify-center text-indigo-400 border border-indigo-500/20">
              <Gavel className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Decisions ({decisions.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Final Agreements</span>
        </div>

        {decisions.length === 0 ? (
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
            No final decisions were identified.
          </div>
        ) : (
          <div className="space-y-2.5">
            {decisions.map((dec) => (
              <div
                key={dec.id}
                className="flex items-start justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 transition-colors"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Decision
                    </span>
                    {dec.date && (
                      <span className="text-[11px] text-slate-500 font-mono">{dec.date}</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-100 font-medium leading-relaxed">
                    {dec.decision}
                  </p>
                </div>

                <button
                  onClick={() => onOpenSource(dec.source)}
                  className="shrink-0 inline-flex items-center gap-1 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-400 hover:text-blue-300 hover:border-blue-500/40 transition-colors cursor-pointer"
                  title="View source citation"
                  aria-label={`View source citation for decision: ${dec.decision.slice(0, 30)}`}
                >
                  <Info className="h-3.5 w-3.5 text-blue-400" />
                  <span className="hidden sm:inline text-[11px]">Source</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 6. Approvals */}
      <section className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="h-3.5 w-3.5" />
            </div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Approvals ({approvals.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500">Formal Sign-offs</span>
        </div>

        {approvals.length === 0 ? (
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
            No explicit approvals were identified.
          </div>
        ) : (
          <div className="space-y-2.5">
            {approvals.map((app) => {
              const hasApprover = Boolean(app.approvedBy && !["Unknown", "—", "Unassigned", "None", ""].includes(app.approvedBy.trim()));

              return (
                <div
                  key={app.id}
                  className="flex items-start justify-between gap-4 rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-4 hover:border-emerald-800/40 transition-colors"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Approved
                      </span>
                      {app.date && (
                        <span className="text-[11px] text-slate-500 font-mono">{app.date}</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-100 font-medium leading-relaxed">
                      {app.decision}
                    </p>
                    {hasApprover && (
                      <div className="flex items-center gap-1 text-xs text-slate-300 pt-0.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        <span>
                          Approved by: <strong className="font-semibold text-white">{app.approvedBy}</strong>
                        </span>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => onOpenSource(app.source)}
                    className="shrink-0 inline-flex items-center gap-1 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-400 hover:text-emerald-300 hover:border-emerald-500/40 transition-colors cursor-pointer"
                    title="View source citation"
                    aria-label={`View source citation for approval: ${app.decision.slice(0, 30)}`}
                  >
                    <Info className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="hidden sm:inline text-[11px]">Source</span>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
