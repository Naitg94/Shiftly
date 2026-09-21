"use client";

import { useMemo } from "react";
import { KeyPointItem, SourceReference } from "@/types/analysis";
import { Info, Tag } from "lucide-react";

interface KeyPointsViewProps {
  keyPoints: KeyPointItem[];
  onOpenSource: (source: SourceReference) => void;
  searchQuery?: string;
  onClearSearch?: () => void;
}

export default function KeyPointsView({
  keyPoints,
  onOpenSource,
  searchQuery = "",
  onClearSearch,
}: KeyPointsViewProps) {
  const query = searchQuery.trim().toLowerCase();

  const filteredKeyPoints = useMemo(() => {
    if (!query) return keyPoints;
    return keyPoints.filter(
      (item) =>
        item.point.toLowerCase().includes(query) ||
        (item.category && item.category.toLowerCase().includes(query))
    );
  }, [keyPoints, query]);

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Extracted Key Points ({filteredKeyPoints.length}
          {query ? ` of ${keyPoints.length}` : ""})
        </h3>
        <span className="text-xs text-slate-500">Filtered for actionable business impact</span>
      </div>

      {filteredKeyPoints.length === 0 ? (
        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/20 text-center space-y-2">
          <p className="text-xs text-slate-400">
            {query
              ? `No key points match "${searchQuery}".`
              : "No key points were identified."}
          </p>
          {query && onClearSearch && (
            <button
              onClick={onClearSearch}
              className="text-xs text-blue-400 hover:text-blue-300 underline cursor-pointer"
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        <ul className="space-y-3">
          {filteredKeyPoints.map((item, index) => (
            <li
              key={item.id}
              className="group relative flex items-start justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 transition-all hover:border-slate-700 hover:bg-slate-900/80"
            >
              <div className="flex items-start gap-3.5 flex-1">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-xs font-semibold text-blue-400 border border-blue-500/20">
                  {index + 1}
                </span>
                <div className="space-y-1.5 flex-1">
                  <p className="text-sm text-slate-200 leading-relaxed">{item.point}</p>
                  {item.category && (
                    <div className="flex items-center gap-1.5">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
                        <Tag className="h-3 w-3 text-slate-500" />
                        {item.category}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Source interaction button */}
              <button
                onClick={() => onOpenSource(item.source)}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-1 text-xs text-slate-400 hover:border-blue-500/40 hover:text-blue-300 hover:bg-slate-900 transition-colors shrink-0 cursor-pointer"
                title="View source context and excerpt"
                aria-label={`View source for key point ${index + 1}`}
              >
                <Info className="h-3.5 w-3.5 text-blue-400" />
                <span className="hidden sm:inline text-[11px]">Source</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
