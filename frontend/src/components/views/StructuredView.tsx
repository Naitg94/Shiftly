"use client";

import { useMemo, useState } from "react";
import {
  ShiftlyAnalysisResult,
  SourceReference,
  DecisionItem,
  KeyPointItem,
  ActionItem,
  ImportantDateItem,
  PendingDecisionItem,
} from "@/types/analysis";
import {
  CheckSquare,
  Gavel,
  Calendar,
  Sparkles,
  Info,
  User,
  Users,
  Clock,
  CheckCircle2,
  FileText,
  ShieldCheck,
} from "lucide-react";

interface StructuredViewProps {
  result: ShiftlyAnalysisResult;
  onOpenSource: (source: SourceReference) => void;
  isFromMemory?: boolean;
  searchQuery?: string;
  onClearSearch?: () => void;
}

function isApprovalItem(item: DecisionItem): boolean {
  const textLower = item.decision.toLowerCase();
  return (
    textLower.includes("approv") ||
    textLower.includes("sign-off") ||
    textLower.includes("signed off") ||
    textLower.includes("authoriz") ||
    textLower.includes("sanction")
  );
}

interface ResponsibilityGroup {
  person: string;
  actions: ActionItem[];
}

type StructuredCategory =
  | "all"
  | "keypoints"
  | "actions"
  | "responsibility"
  | "dates"
  | "decisions"
  | "pending"
  | "approvals";

export default function StructuredView({
  result,
  onOpenSource,
  isFromMemory = false,
  searchQuery = "",
  onClearSearch,
}: StructuredViewProps) {
  const [activeCategory, setActiveCategory] = useState<StructuredCategory>("all");

  // Separate decisions and approvals
  const { rawDecisions, rawApprovals } = useMemo(() => {
    const decs: DecisionItem[] = [];
    const apps: DecisionItem[] = [];

    (result.decisions || []).forEach((item) => {
      if (isApprovalItem(item)) {
        apps.push(item);
      } else {
        decs.push(item);
      }
    });

    return { rawDecisions: decs, rawApprovals: apps };
  }, [result.decisions]);

  const rawKeyPoints = result.keyPoints || [];
  const rawActions = result.actions || [];
  const rawDates = result.importantDates || [];
  const rawPendingDecisions = result.pendingDecisions || [];
  const rawSummary = result.summary?.trim() || "";

  // Exact 8 Structured categories in required order
  const categories: { id: StructuredCategory; label: string }[] = useMemo(() => [
    { id: "all", label: "All" },
    { id: "keypoints", label: "Key Points" },
    { id: "actions", label: "Actions" },
    { id: "responsibility", label: "Responsibility" },
    { id: "dates", label: "Dates" },
    { id: "decisions", label: "Decisions" },
    { id: "pending", label: "Pending Decisions" },
    { id: "approvals", label: "Approvals" },
  ], []);

  const query = searchQuery.trim().toLowerCase();

  // Filtered Summary
  const summaryMatches = useMemo(() => {
    if (!query) return Boolean(rawSummary);
    return rawSummary.toLowerCase().includes(query);
  }, [rawSummary, query]);

  // Filtered Key Points (preserving original extracted order)
  const keyPoints = useMemo(() => {
    if (!query) return rawKeyPoints;
    return rawKeyPoints.filter(
      (kp) =>
        kp.point.toLowerCase().includes(query) ||
        (kp.category && kp.category.toLowerCase().includes(query))
    );
  }, [rawKeyPoints, query]);

  // Filtered Actions (preserving original extracted order)
  const actions = useMemo(() => {
    if (!query) return rawActions;
    return rawActions.filter(
      (act) =>
        act.action.toLowerCase().includes(query) ||
        act.responsiblePerson.toLowerCase().includes(query) ||
        (act.deadline && act.deadline.toLowerCase().includes(query))
    );
  }, [rawActions, query]);

  // Responsibility Groups derived from actions
  const responsibilityGroups: ResponsibilityGroup[] = useMemo(() => {
    const groupMap = new Map<string, ActionItem[]>();

    (rawActions || []).forEach((act) => {
      const person =
        act.responsiblePerson &&
        !["Unassigned", "Unknown", "None", ""].includes(act.responsiblePerson.trim())
          ? act.responsiblePerson.trim()
          : "Unassigned";

      if (!groupMap.has(person)) {
        groupMap.set(person, []);
      }
      groupMap.get(person)!.push(act);
    });

    let groups: ResponsibilityGroup[] = [];
    groupMap.forEach((acts, person) => {
      groups.push({ person, actions: acts });
    });

    if (query) {
      groups = groups
        .map((g) => {
          const personMatches = g.person.toLowerCase().includes(query);
          const matchedActions = g.actions.filter(
            (act) =>
              personMatches ||
              act.action.toLowerCase().includes(query) ||
              (act.deadline && act.deadline.toLowerCase().includes(query))
          );
          return { person: g.person, actions: matchedActions };
        })
        .filter((g) => g.actions.length > 0);
    }

    return groups;
  }, [rawActions, query]);

  // Filtered Important Dates (preserving original extracted order)
  const importantDates = useMemo(() => {
    if (!query) return rawDates;
    return rawDates.filter(
      (dt) =>
        dt.title.toLowerCase().includes(query) ||
        dt.date.toLowerCase().includes(query) ||
        dt.significance.toLowerCase().includes(query)
    );
  }, [rawDates, query]);

  // Filtered Decisions (preserving original extracted order)
  const decisions = useMemo(() => {
    if (!query) return rawDecisions;
    return rawDecisions.filter(
      (dec) =>
        dec.decision.toLowerCase().includes(query) ||
        dec.approvedBy.toLowerCase().includes(query) ||
        (dec.date && dec.date.toLowerCase().includes(query))
    );
  }, [rawDecisions, query]);

  // Filtered Approvals (preserving original extracted order)
  const approvals = useMemo(() => {
    if (!query) return rawApprovals;
    return rawApprovals.filter(
      (app) =>
        app.decision.toLowerCase().includes(query) ||
        app.approvedBy.toLowerCase().includes(query) ||
        (app.date && app.date.toLowerCase().includes(query))
    );
  }, [rawApprovals, query]);

  // Filtered Pending Decisions (preserving original extracted order)
  const pendingDecisions = useMemo(() => {
    if (!query) return rawPendingDecisions;
    return rawPendingDecisions.filter(
      (pd) =>
        pd.decision.toLowerCase().includes(query) ||
        (pd.status && pd.status.toLowerCase().includes(query))
    );
  }, [rawPendingDecisions, query]);

  // Matches within the currently visible/filtered Structured content
  const visibleMatches = useMemo(() => {
    switch (activeCategory) {
      case "keypoints":
        return keyPoints.length;
      case "actions":
        return actions.length;
      case "responsibility":
        return responsibilityGroups.length;
      case "dates":
        return importantDates.length;
      case "decisions":
        return decisions.length;
      case "pending":
        return pendingDecisions.length;
      case "approvals":
        return approvals.length;
      case "all":
      default:
        return (
          (summaryMatches ? 1 : 0) +
          keyPoints.length +
          actions.length +
          importantDates.length +
          decisions.length +
          approvals.length +
          pendingDecisions.length
        );
    }
  }, [
    activeCategory,
    summaryMatches,
    keyPoints.length,
    actions.length,
    responsibilityGroups.length,
    importantDates.length,
    decisions.length,
    approvals.length,
    pendingDecisions.length,
  ]);

  return (
    <div className="space-y-10 animate-in fade-in duration-200">
      {/* Category Filter Bar */}
      <div className="flex items-center gap-1.5 flex-wrap p-2 rounded-2xl bg-slate-900/50 border border-slate-800">
        {categories.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveCategory(c.id)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer border whitespace-nowrap ${
              activeCategory === c.id
                ? "bg-blue-600 border-blue-500 text-white shadow-sm shadow-blue-600/20 font-semibold"
                : "bg-slate-900/80 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <span>{c.label}</span>
          </button>
        ))}
      </div>

      {/* Empty State when search has 0 matches in the active category */}
      {query && visibleMatches === 0 && (
        <div className="p-8 rounded-2xl border border-slate-800 bg-slate-900/30 text-center space-y-3">
          <p className="text-sm text-slate-400">
            No intelligence items match &ldquo;{searchQuery}&rdquo;
            {activeCategory !== "all"
              ? ` in ${categories.find((c) => c.id === activeCategory)?.label || "this category"}`
              : ""}.
          </p>
          {onClearSearch && (
            <button
              onClick={onClearSearch}
              className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
            >
              Clear search
            </button>
          )}
        </div>
      )}

      {/* 1. Analysis Summary */}
      {activeCategory === "all" && (isFromMemory || Boolean(rawSummary)) && (!query || summaryMatches) && (
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
              {rawSummary || "No executive summary available for this project."}
            </p>
          </div>
        </section>
      )}

      {/* 2. Key Points */}
      {(activeCategory === "all" || activeCategory === "keypoints") && (activeCategory === "keypoints" || isFromMemory || rawKeyPoints.length > 0) && (!query || keyPoints.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
                <Sparkles className="h-3.5 w-3.5" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Key Points ({keyPoints.length})
              </h3>
            </div>
            <span className="text-xs text-slate-500">Essential Takeaways</span>
          </div>

          {keyPoints.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
              No key points recorded for this project.
            </div>
          ) : (
            <ul className="space-y-2.5">
              {keyPoints.map((kp, idx) => (
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
      )}

      {/* 3. Action Items */}
      {(activeCategory === "all" || activeCategory === "actions") && (activeCategory === "actions" || isFromMemory || rawActions.length > 0) && (!query || actions.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
                <CheckSquare className="h-3.5 w-3.5" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Action Items ({actions.length})
              </h3>
            </div>
            <span className="text-xs text-slate-500">What &bull; Who &bull; When</span>
          </div>

          {actions.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
              No explicit tasks or commitments recorded for this project.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {actions.map((act) => {
                const hasOwner =
                  act.responsiblePerson &&
                  !["Unassigned", "Unknown", "None", ""].includes(act.responsiblePerson.trim());
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
                        <span
                          className={`truncate font-medium ${
                            hasOwner ? "text-slate-200" : "text-slate-500 italic"
                          }`}
                        >
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
      )}

      {/* 4. Dedicated Responsibility Section */}
      {(activeCategory === "all" || activeCategory === "responsibility") && (activeCategory === "responsibility" || isFromMemory || responsibilityGroups.length > 0) && (!query || responsibilityGroups.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/20">
                <Users className="h-3.5 w-3.5" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Responsibility ({responsibilityGroups.length})
              </h3>
            </div>
            <span className="text-xs text-slate-500">Assigned Commitments</span>
          </div>

          {responsibilityGroups.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
              No assigned commitments recorded for this project.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {responsibilityGroups.map((group) => (
                <div
                  key={group.person}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3 hover:border-slate-700 transition-colors flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <div className="h-6 w-6 rounded-full bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/20 text-xs font-semibold">
                          <User className="h-3 w-3" />
                        </div>
                        <span className="text-sm font-semibold text-slate-100">
                          {group.person}
                        </span>
                      </div>
                      <span className="text-[11px] font-medium text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
                        {group.actions.length} {group.actions.length === 1 ? "task" : "tasks"}
                      </span>
                    </div>

                    <ul className="space-y-2">
                      {group.actions.map((act) => (
                        <li
                          key={act.id}
                          className="flex items-start justify-between gap-2.5 text-xs text-slate-300 bg-slate-950/40 rounded-lg p-2.5 border border-slate-800/60"
                        >
                          <div className="space-y-1 flex-1">
                            <p className="leading-relaxed">{act.action}</p>
                            {act.deadline && (
                              <span className="inline-block text-[10px] font-mono text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                                Due {act.deadline}
                              </span>
                            )}
                          </div>
                          <button
                            onClick={() => onOpenSource(act.source)}
                            className="shrink-0 p-1 text-slate-500 hover:text-blue-400 rounded transition-colors cursor-pointer"
                            title="View source citation"
                            aria-label={`View source citation for action: ${act.action.slice(0, 30)}`}
                          >
                            <Info className="h-3.5 w-3.5" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* 5. Important Dates */}
      {(activeCategory === "all" || activeCategory === "dates") && (activeCategory === "dates" || isFromMemory || rawDates.length > 0) && (!query || importantDates.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-purple-500/10 flex items-center justify-center text-purple-400 border border-purple-500/20">
                <Calendar className="h-3.5 w-3.5" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Important Dates ({importantDates.length})
              </h3>
            </div>
            <span className="text-xs text-slate-500">Project Milestones</span>
          </div>

          {importantDates.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
              No project-critical dates recorded for this project.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {importantDates.map((dt) => (
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
      )}

      {/* 6. Decisions */}
      {(activeCategory === "all" || activeCategory === "decisions") && (activeCategory === "decisions" || isFromMemory || rawDecisions.length > 0) && (!query || decisions.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
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
              No final decisions recorded for this project.
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
                    {dec.approvedBy &&
                      !["Unknown", "—", "Unassigned", "None", ""].includes(dec.approvedBy.trim()) && (
                        <div className="text-xs text-slate-400 pt-0.5">
                          Decided / Agreed by: <span className="text-slate-200 font-medium">{dec.approvedBy}</span>
                        </div>
                      )}
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
      )}

      {/* 7. Approvals */}
      {(activeCategory === "all" || activeCategory === "approvals") && (activeCategory === "approvals" || isFromMemory || rawApprovals.length > 0) && (!query || approvals.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
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
              No explicit approvals recorded for this project.
            </div>
          ) : (
            <div className="space-y-2.5">
              {approvals.map((app) => {
                const hasApprover = Boolean(
                  app.approvedBy &&
                    !["Unknown", "—", "Unassigned", "None", ""].includes(app.approvedBy.trim())
                );

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
      )}

      {/* 8. Pending Decisions */}
      {(activeCategory === "all" || activeCategory === "pending") && (activeCategory === "pending" || isFromMemory || rawPendingDecisions.length > 0) && (!query || pendingDecisions.length > 0) && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
                <Clock className="h-3.5 w-3.5" />
              </div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Pending Decisions ({pendingDecisions.length})
              </h3>
            </div>
            <span className="text-xs text-slate-500">Awaiting Resolution</span>
          </div>

          {pendingDecisions.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 text-xs text-slate-400">
              No pending decisions for this project.
            </div>
          ) : (
            <div className="space-y-2.5">
              {pendingDecisions.map((pd) => (
                <div
                  key={pd.id}
                  className="flex items-start justify-between gap-4 rounded-xl border border-amber-900/30 bg-amber-950/10 p-4 hover:border-amber-800/40 transition-colors"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Pending
                      </span>
                      {pd.status && pd.status !== "Pending" && (
                        <span className="text-[11px] text-slate-500 font-mono">{pd.status}</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-100 font-medium leading-relaxed">
                      {pd.decision}
                    </p>
                  </div>

                  <button
                    onClick={() => onOpenSource(pd.source)}
                    className="shrink-0 inline-flex items-center gap-1 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-400 hover:text-amber-300 hover:border-amber-500/40 transition-colors cursor-pointer"
                    title="View source citation"
                    aria-label={`View source citation for pending decision: ${pd.decision.slice(0, 30)}`}
                  >
                    <Info className="h-3.5 w-3.5 text-amber-400" />
                    <span className="hidden sm:inline text-[11px]">Source</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
