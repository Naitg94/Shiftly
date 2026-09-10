"use client";

import { Sparkles, Database } from "lucide-react";

interface NavbarProps {
  onReset: () => void;
  isResultsState: boolean;
}

export default function Navbar({ onReset, isResultsState }: NavbarProps) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div
          onClick={onReset}
          className="flex cursor-pointer items-center space-x-3 transition-opacity hover:opacity-90"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-lg shadow-md shadow-blue-500/20">
            S
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">Shiftly</span>
              <span className="text-[10px] font-medium uppercase tracking-wider rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
                Beta
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-none">Find what matters.</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex items-center gap-2 sm:gap-4 text-sm">
          <button
            onClick={onReset}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
              !isResultsState
                ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                : "text-slate-300 hover:text-white hover:bg-slate-900"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Analyze</span>
          </button>

          {/* Memory Placeholder */}
          <div className="relative group flex items-center">
            <button
              disabled
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-500 cursor-not-allowed hover:bg-slate-900/50"
              title="Project Memory will be introduced in Phase 2"
            >
              <Database className="h-3.5 w-3.5" />
              <span>Project Memory</span>
              <span className="text-[10px] font-normal uppercase tracking-wider rounded bg-slate-800/80 px-1.5 py-0.2 text-slate-400">
                Phase 2
              </span>
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
}
