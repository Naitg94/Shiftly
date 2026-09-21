"use client";

import { useMemo } from "react";
import { ShiftlyAnalysisResult } from "@/types/analysis";
import { FileText, CheckCircle2, Clock } from "lucide-react";

interface SummaryViewProps {
  result: ShiftlyAnalysisResult;
  searchQuery?: string;
  onClearSearch?: () => void;
}

function highlightText(text: string, query: string) {
  if (!query.trim() || !text) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  const parts = text.split(regex);
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="bg-amber-500/30 text-amber-200 px-0.5 rounded font-medium">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

export default function SummaryView({ result, searchQuery = "", onClearSearch }: SummaryViewProps) {
  const query = searchQuery.trim().toLowerCase();

  const matchCount = useMemo(() => {
    if (!query) return 0;
    let count = 0;
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(escaped, "gi");

    const countMatches = (str: string) => {
      const m = str.match(regex);
      return m ? m.length : 0;
    };

    count += countMatches(result.summary || "");

    if (result.decisions.length > 0) {
      count += countMatches(result.decisions[0].decision || "");
      if (result.decisions[0].approvedBy) {
        count += countMatches(result.decisions[0].approvedBy);
      }
    }

    if (result.importantDates.length > 0) {
      count += countMatches(result.importantDates[0].title || "");
      count += countMatches(result.importantDates[0].date || "");
    } else if (result.actions.length > 0) {
      count += countMatches(result.actions[0].action || "");
      if (result.actions[0].responsiblePerson) {
        count += countMatches(result.actions[0].responsiblePerson);
      }
    }

    return count;
  }, [result, query]);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {query && (
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span>
            {matchCount > 0 ? (
              <>
                Found <strong className="text-slate-200">{matchCount}</strong> match{matchCount === 1 ? "" : "es"} for &ldquo;{searchQuery}&rdquo;
              </>
            ) : (
              <>No matches found for &ldquo;{searchQuery}&rdquo;</>
            )}
          </span>
          {onClearSearch && (
            <button
              onClick={onClearSearch}
              className="text-blue-400 hover:text-blue-300 underline cursor-pointer"
            >
              Clear
            </button>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Executive Summary
        </h3>
        <span className="text-xs text-slate-500">
          Condensed from {result.stats.messagesAnalyzed} messages
        </span>
      </div>

      {/* Main Paragraph */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8 space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
          <FileText className="h-4 w-4" />
          <span>Synthesis</span>
        </div>
        <p className="text-base sm:text-lg text-slate-200 leading-relaxed font-normal">
          {highlightText(result.summary, query)}
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
                {highlightText(result.decisions[0].decision, query)}
                {result.decisions[0].approvedBy && result.decisions[0].approvedBy !== "Unknown" && (
                  <span className="text-slate-500 ml-1.5">
                    (Approved by {highlightText(result.decisions[0].approvedBy, query)})
                  </span>
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
                <span className="font-mono text-amber-300 mr-1.5">
                  {highlightText(result.importantDates[0].date, query)}
                </span>
                — {highlightText(result.importantDates[0].title, query)}
              </p>
            </div>
          ) : result.actions.length > 0 ? (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 p-4 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-medium text-amber-400">
                <Clock className="h-4 w-4" />
                <span>Immediate Action</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {highlightText(result.actions[0].action, query)}
                {result.actions[0].responsiblePerson && result.actions[0].responsiblePerson !== "Unassigned" && (
                  <span className="text-slate-500 ml-1.5">
                    ({highlightText(result.actions[0].responsiblePerson, query)})
                  </span>
                )}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
