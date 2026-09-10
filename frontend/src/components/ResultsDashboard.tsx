"use client";

import { useState } from "react";
import {
  ShiftlyAnalysisResult,
  SourceReference,
} from "@/types/analysis";
import {
  ListChecks,
  FileText,
  Table,
  LayoutGrid,
  RotateCcw,
  MessageSquare,
  Sparkles,
  Calendar,
  Gavel,
  CheckSquare,
} from "lucide-react";
import KeyPointsView from "./views/KeyPointsView";
import SummaryView from "./views/SummaryView";
import TableView from "./views/TableView";
import StructuredView from "./views/StructuredView";
import SourceModal from "./SourceModal";

interface ResultsDashboardProps {
  result: ShiftlyAnalysisResult;
  onReset: () => void;
}

type ViewMode = "keypoints" | "summary" | "table" | "structured";

export default function ResultsDashboard({
  result,
  onReset,
}: ResultsDashboardProps) {
  const [activeView, setActiveView] = useState<ViewMode>("keypoints");
  const [selectedSource, setSelectedSource] = useState<SourceReference | null>(null);

  const tabs: { id: ViewMode; label: string; icon: React.ReactNode }[] = [
    { id: "keypoints", label: "Key Points", icon: <ListChecks className="h-4 w-4" /> },
    { id: "summary", label: "Summary", icon: <FileText className="h-4 w-4" /> },
    { id: "table", label: "Table", icon: <Table className="h-4 w-4" /> },
    { id: "structured", label: "Structured", icon: <LayoutGrid className="h-4 w-4" /> },
  ];

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              <Sparkles className="h-3 w-3" />
              Intelligence Extracted
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400">{result.analyzedAt}</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {result.title}
          </h2>
        </div>

        {/* Reset / New Analysis */}
        <button
          onClick={onReset}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs sm:text-sm font-medium text-slate-200 hover:bg-slate-800 hover:text-white transition-colors self-start sm:self-auto shadow-sm"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>New Analysis</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {/* Messages Analyzed */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
            <span>Analyzed</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.messagesAnalyzed}
            <span className="text-xs font-normal text-slate-500 ml-1">msgs</span>
          </div>
        </div>

        {/* Key Points */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Sparkles className="h-3.5 w-3.5 text-blue-400" />
            <span>Key Points</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.keyPointsCount}
          </div>
        </div>

        {/* Actions */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <CheckSquare className="h-3.5 w-3.5 text-amber-400" />
            <span>Actions</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.actionsCount}
          </div>
        </div>

        {/* Decisions */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Gavel className="h-3.5 w-3.5 text-emerald-400" />
            <span>Decisions</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.decisionsCount}
          </div>
        </div>

        {/* Important Dates */}
        <div className="col-span-2 sm:col-span-1 rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Calendar className="h-3.5 w-3.5 text-purple-400" />
            <span>Key Dates</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.importantDatesCount}
          </div>
        </div>
      </div>

      {/* Main Results Container */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl shadow-black/40 p-5 sm:p-7 space-y-6">
        {/* View Switcher Tabs */}
        <div className="flex items-center justify-start border-b border-slate-800 pb-4 overflow-x-auto gap-2">
          {tabs.map((tab) => {
            const isActive = activeView === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveView(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/80"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Active View Render */}
        <div className="pt-2">
          {activeView === "keypoints" && (
            <KeyPointsView
              keyPoints={result.keyPoints}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
          {activeView === "summary" && <SummaryView result={result} />}
          {activeView === "table" && (
            <TableView
              result={result}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
          {activeView === "structured" && (
            <StructuredView
              result={result}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
        </div>
      </div>

      {/* Granular Source Modal */}
      <SourceModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />
    </div>
  );
}
