"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import InputSection from "@/components/InputSection";
import ProcessingState from "@/components/ProcessingState";
import ResultsDashboard from "@/components/ResultsDashboard";
import { MOCK_ANALYSIS_RESULT } from "@/data/mockData";
import { ShiftlyAnalysisResult } from "@/types/analysis";
import { Layers } from "lucide-react";

type AppStage = "input" | "processing" | "results";

export default function Home() {
  const [stage, setStage] = useState<AppStage>("input");
  const [inputText, setInputText] = useState("");
  const [analysisResult, setAnalysisResult] = useState<ShiftlyAnalysisResult>(MOCK_ANALYSIS_RESULT);

  const handleStartAnalysis = () => {
    setStage("processing");
  };

  const handleProcessingComplete = () => {
    setStage("results");
  };

  const handleReset = () => {
    setStage("input");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* SaaS Navigation */}
      <Navbar onReset={handleReset} isResultsState={stage === "results"} />

      {/* Main Content Body */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 flex flex-col justify-start">
        {stage === "input" && (
          <InputSection
            inputText={inputText}
            setInputText={setInputText}
            onAnalyze={handleStartAnalysis}
          />
        )}

        {stage === "processing" && (
          <ProcessingState onComplete={handleProcessingComplete} />
        )}

        {stage === "results" && (
          <ResultsDashboard
            result={analysisResult}
            onReset={handleReset}
          />
        )}
      </main>

      {/* Minimal Footer */}
      <footer className="w-full border-t border-slate-900 bg-slate-950/50 py-6 text-xs text-slate-500">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">Shiftly</span>
            <span>—</span>
            <span>Find what matters.</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-500">
            <Layers className="h-3 w-3 text-slate-500" />
            <span>Communication Intelligence Layer</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
